from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..addresses import normalize_address
from ..db import get_db
from ..deps import current_account
from ..models import Account, Customer, Property
from ..schemas import (CustomerIn, CustomerOut, CustomerSummary, CustomerUpdate,
                       PropertyIn, PropertyOut)

router = APIRouter(prefix="/api", tags=["customers"])


def _get_customer(db: Session, account: Account, customer_id: int) -> Customer:
    customer = db.scalar(
        select(Customer).options(selectinload(Customer.properties))
        .where(Customer.id == customer_id, Customer.account_id == account.id))
    if customer is None:
        raise HTTPException(404, "Customer not found")
    return customer


def _get_property(db: Session, account: Account, property_id: int) -> Property:
    prop = db.scalar(select(Property).where(Property.id == property_id,
                                            Property.account_id == account.id))
    if prop is None:
        raise HTTPException(404, "Property not found")
    return prop


def _clean_email(email: str) -> str:
    return email.strip().lower()


def _new_property(account: Account, customer: Customer, data: PropertyIn) -> Property:
    prop = Property(account_id=account.id, address_norm=normalize_address(data.address),
                    **data.model_dump())
    customer.properties.append(prop)
    return prop


@router.get("/customers", response_model=list[CustomerSummary])
def list_customers(q: str = "", include_inactive: bool = False,
                   account: Account = Depends(current_account), db: Session = Depends(get_db)):
    stmt = (select(Customer).options(selectinload(Customer.properties))
            .where(Customer.account_id == account.id).order_by(func.lower(Customer.name)))
    if not include_inactive:
        stmt = stmt.where(Customer.active.is_(True))
    if q.strip():
        like = f"%{q.strip().lower()}%"
        matching_props = select(Property.customer_id).where(
            Property.account_id == account.id, func.lower(Property.address).like(like))
        stmt = stmt.where(or_(func.lower(Customer.name).like(like),
                              func.lower(Customer.email).like(like),
                              func.lower(Customer.phone).like(like),
                              Customer.id.in_(matching_props)))
    out = []
    for c in db.scalars(stmt):
        out.append(CustomerSummary(
            id=c.id, name=c.name, email=c.email, phone=c.phone, active=c.active,
            property_count=len(c.properties),
            first_address=c.properties[0].address if c.properties else ""))
    return out


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(body: CustomerIn, account: Account = Depends(current_account),
                    db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"properties"})
    data["email"] = _clean_email(data["email"])
    customer = Customer(account_id=account.id, **data)
    db.add(customer)
    for prop in body.properties:
        _new_property(account, customer, prop)
    db.commit()
    return _get_customer(db, account, customer.id)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, account: Account = Depends(current_account),
                 db: Session = Depends(get_db)):
    return _get_customer(db, account, customer_id)


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, body: CustomerUpdate,
                    account: Account = Depends(current_account), db: Session = Depends(get_db)):
    customer = _get_customer(db, account, customer_id)
    for key, value in body.model_dump().items():
        setattr(customer, key, _clean_email(value) if key == "email" else value)
    db.commit()
    return _get_customer(db, account, customer_id)


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(customer_id: int, account: Account = Depends(current_account),
                    db: Session = Depends(get_db)):
    db.delete(_get_customer(db, account, customer_id))
    db.commit()


@router.post("/customers/{customer_id}/properties", response_model=PropertyOut, status_code=201)
def add_property(customer_id: int, body: PropertyIn,
                 account: Account = Depends(current_account), db: Session = Depends(get_db)):
    customer = _get_customer(db, account, customer_id)
    prop = _new_property(account, customer, body)
    db.commit()
    return prop


@router.put("/properties/{property_id}", response_model=PropertyOut)
def update_property(property_id: int, body: PropertyIn,
                    account: Account = Depends(current_account), db: Session = Depends(get_db)):
    prop = _get_property(db, account, property_id)
    changed_address = normalize_address(body.address) != prop.address_norm
    for key, value in body.model_dump().items():
        setattr(prop, key, value)
    prop.address_norm = normalize_address(body.address)
    if changed_address:
        prop.lat = prop.lng = None  # address moved; the geocoder will fill these in again
    db.commit()
    return prop


@router.delete("/properties/{property_id}", status_code=204)
def delete_property(property_id: int, account: Account = Depends(current_account),
                    db: Session = Depends(get_db)):
    db.delete(_get_property(db, account, property_id))
    db.commit()
