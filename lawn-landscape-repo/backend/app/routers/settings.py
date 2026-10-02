from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_account
from ..models import Account, Settings
from ..schemas import SettingsIn, SettingsOut
from ..security import encrypt_secret

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _out(account: Account, s: Settings) -> SettingsOut:
    return SettingsOut(
        business_name=account.business_name, timezone=account.timezone,
        base_address=s.base_address,
        base_lat=float(s.base_lat) if s.base_lat is not None else None,
        base_lng=float(s.base_lng) if s.base_lng is not None else None,
        rate_per_1000_sqft=float(s.rate_per_1000_sqft),
        travel_charge_per_minute=float(s.travel_charge_per_minute),
        min_visit_price=float(s.min_visit_price), tax_rate_percent=float(s.tax_rate_percent),
        late_fee_type=s.late_fee_type, late_fee_value=float(s.late_fee_value),
        late_fee_grace_days=s.late_fee_grace_days, gmail_address=s.gmail_address,
        gmail_password_set=bool(s.gmail_app_password_enc))


@router.get("", response_model=SettingsOut)
def get_settings(account: Account = Depends(current_account), db: Session = Depends(get_db)):
    return _out(account, db.get(Settings, account.id))


@router.put("", response_model=SettingsOut)
def put_settings(body: SettingsIn, account: Account = Depends(current_account),
                 db: Session = Depends(get_db)):
    try:
        ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(400, "Unknown timezone. Use a name like America/Chicago.")
    s = db.get(Settings, account.id)
    account.business_name = body.business_name
    account.timezone = body.timezone
    if body.base_address.strip() != s.base_address:
        s.base_lat = s.base_lng = None  # phase 2 geocodes the new base address
    s.base_address = body.base_address.strip()
    for key in ("rate_per_1000_sqft", "travel_charge_per_minute", "min_visit_price",
                "tax_rate_percent", "late_fee_type", "late_fee_value", "late_fee_grace_days"):
        setattr(s, key, getattr(body, key))
    s.gmail_address = body.gmail_address.strip()
    if body.gmail_app_password is not None:
        s.gmail_app_password_enc = encrypt_secret(body.gmail_app_password.replace(" ", ""))
    db.commit()
    return _out(account, s)
