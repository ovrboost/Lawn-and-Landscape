import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from .config import config
from .db import Base, SessionLocal, engine
from .models import Account, Settings
from .routers import auth, customers, importer, settings
from .security import hash_password


def seed() -> None:
    """Create the one account and its settings the first time the app starts."""
    with SessionLocal() as db:
        account = db.scalars(select(Account)).first()
        if account is None:
            account = Account(business_name=config.business_name, timezone=config.timezone,
                              password_hash=hash_password(config.app_password))
            db.add(account)
            db.flush()
        if db.get(Settings, account.id) is None:
            db.add(Settings(account_id=account.id, base_address=config.base_address))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed()
    yield


app = FastAPI(title="Lawn & Landscape", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=config.secret_key, https_only=config.cookie_secure,
                   same_site="lax", max_age=60 * 60 * 24 * 30, session_cookie="lawn_session")

for module in (auth, customers, importer, settings):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    """Serve the built PWA; unknown paths fall back to index.html so app routes work on reload."""
    if path.startswith("api/"):
        raise HTTPException(404)
    root = os.path.abspath(config.static_dir)
    candidate = os.path.abspath(os.path.join(root, path))
    if path and candidate.startswith(root + os.sep) and os.path.isfile(candidate):
        target = candidate
    else:
        target = os.path.join(root, "index.html")
    if not os.path.isfile(target):
        raise HTTPException(404, "Frontend not built")
    headers = {}
    if os.path.basename(target) in ("index.html", "sw.js", "manifest.webmanifest"):
        headers["Cache-Control"] = "no-cache"
    return FileResponse(target, headers=headers)
