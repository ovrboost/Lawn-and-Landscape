from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_account
from ..models import Account
from ..schemas import LoginIn, PasswordChangeIn
from ..security import hash_password, throttle, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = request.client.host if request.client else "unknown"
    if throttle.blocked(key):
        raise HTTPException(429, "Too many attempts. Wait a minute and try again.")
    account = db.scalars(select(Account).order_by(Account.id)).first()
    if account is None or not verify_password(body.password, account.password_hash):
        throttle.record_failure(key)
        raise HTTPException(401, "Wrong password")
    throttle.clear(key)
    request.session["account_id"] = account.id
    return {"ok": True, "business_name": account.business_name}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(account: Account = Depends(current_account)):
    return {"business_name": account.business_name, "timezone": account.timezone}


@router.post("/password")
def change_password(body: PasswordChangeIn, account: Account = Depends(current_account),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, account.password_hash):
        raise HTTPException(400, "Current password is wrong")
    account.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
