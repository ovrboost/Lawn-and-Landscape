from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import Account


def current_account(request: Request, db: Session = Depends(get_db)) -> Account:
    account_id = request.session.get("account_id")
    account = db.get(Account, account_id) if account_id else None
    if account is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return account
