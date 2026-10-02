import csv
import io
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..addresses import normalize_address
from ..db import get_db
from ..deps import current_account
from ..models import Account, Customer, Property
from ..schemas import (ImportCommit, ImportCommitResult, ImportPreview, ImportRow,
                       ImportRowResult)

router = APIRouter(prefix="/api/import", tags=["import"])

MAX_BYTES = 2_000_000
MAX_ROWS = 2000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

TEMPLATE = (
    "name,email,phone,address,billing_mode,monthly_rate,per_visit_price,lot_size_sqft,notes\n"
    "Jane Smith,jane@example.com,636-555-0100,\"1213 Arbor Ln, Pacific, MO 63069\",monthly_flat,180,,9000,Gate code 1234\n"
    "Bob Jones,bob@example.com,636-555-0101,\"45 Oak St, Washington, MO 63090\",per_visit,,55,6500,\n"
)

ALIASES = {
    "name": ["name", "customer", "customer name", "full name"],
    "email": ["email", "e-mail", "email address"],
    "phone": ["phone", "phone number", "mobile", "cell", "telephone"],
    "address": ["address", "service address", "property address", "street address", "street"],
    "city": ["city", "town"],
    "state": ["state", "st"],
    "zip": ["zip", "zip code", "zipcode", "postal code"],
    "billing_address": ["billing address", "billing_address"],
    "lot_size_sqft": ["lot size", "lot_size_sqft", "lot size sqft", "sqft", "lot sqft"],
    "billing_mode": ["billing mode", "billing_mode", "billing type"],
    "monthly_rate": ["monthly rate", "monthly_rate", "monthly"],
    "per_visit_price": ["per visit price", "per_visit_price", "per visit", "price per visit"],
    "notes": ["notes", "note", "comments"],
}


def _header_map(fieldnames: list[str]) -> dict[str, str]:
    lookup = {}
    for field, names in ALIASES.items():
        for n in names:
            lookup[n] = field
    mapping = {}
    for raw in fieldnames:
        key = re.sub(r"[\s_]+", " ", (raw or "").strip().lower())
        key2 = key.replace(" ", "_")
        field = lookup.get(key) or lookup.get(key2)
        if field and field not in mapping.values():
            mapping[raw] = field
    return mapping


def _money(value: str) -> float | None:
    value = (value or "").replace("$", "").replace(",", "").strip()
    if not value:
        return None
    return float(value)


def _int(value: str) -> int | None:
    value = (value or "").replace(",", "").strip()
    if not value:
        return None
    return int(float(value))


def parse_csv(raw: bytes) -> tuple[list[ImportRow], list[ImportRowResult]]:
    """Return rows that parsed, plus rows that are broken beyond use (bad numbers)."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "The file is empty")
    mapping = _header_map(reader.fieldnames)
    if "name" not in mapping.values():
        raise HTTPException(400, "No name column found. Download the template to see the expected columns.")
    rows, broken = [], []
    for i, rec in enumerate(reader, start=2):
        if i - 1 > MAX_ROWS:
            raise HTTPException(400, f"Too many rows (limit {MAX_ROWS}). Split the file.")
        vals = {field: (rec.get(raw_name) or "").strip() for raw_name, field in mapping.items()}
        if not any(vals.values()):
            continue
        address = vals.get("address", "")
        extras = [vals.get("city", ""), " ".join(p for p in (vals.get("state", ""), vals.get("zip", "")) if p)]
        extras = [e for e in extras if e]
        low = address.lower()
        if address and extras and not any(e.lower() in low for e in extras if e):
            address = ", ".join([address] + extras)
        mode_raw = re.sub(r"[\s-]+", "_", vals.get("billing_mode", "").lower())
        errors = []
        try:
            monthly = _money(vals.get("monthly_rate", ""))
            per_visit = _money(vals.get("per_visit_price", ""))
            lot = _int(vals.get("lot_size_sqft", ""))
        except ValueError:
            monthly = per_visit = lot = None
            errors.append("A number column (rate, price, or lot size) is not a number")
        if mode_raw in ("per_visit", "visit"):
            mode = "per_visit"
        elif mode_raw in ("monthly_flat", "monthly", "flat"):
            mode = "monthly_flat"
        else:
            mode = "per_visit" if (per_visit and not monthly) else "monthly_flat"
        row = ImportRow(line=i, name=vals.get("name", ""), email=vals.get("email", "").lower(),
                        phone=vals.get("phone", ""), address=address,
                        billing_address=vals.get("billing_address", ""), lot_size_sqft=lot,
                        billing_mode=mode, monthly_rate=monthly, per_visit_price=per_visit,
                        notes=vals.get("notes", ""))
        if errors:
            broken.append(ImportRowResult(**row.model_dump(), status="error", errors=errors))
        else:
            rows.append(row)
    return rows, broken


def process(rows: list[ImportRow], db: Session, account: Account, apply: bool):
    """Decide each row's fate; with apply=True also write the new customers and properties.

    A customer matches on email (or on name when the row has no email). A property matches on
    normalized address under that customer. A row is skipped only when both already exist, so a
    second address for the same email becomes a new property.
    """
    existing = db.scalars(select(Customer).options(selectinload(Customer.properties))
                          .where(Customer.account_id == account.id)).all()
    by_key: dict[tuple[str, str], Customer | None] = {}
    seen_props: set[tuple[tuple[str, str], str]] = set()
    for c in existing:
        key = ("e", c.email.lower()) if c.email else ("n", c.name.strip().lower())
        by_key[key] = c
        for p in c.properties:
            seen_props.add((key, p.address_norm))

    results, created_c, created_p, skipped, errs = [], 0, 0, 0, 0
    for row in rows:
        warnings, errors = [], []
        if not row.name.strip():
            errors.append("Name is missing")
        if row.email and not EMAIL_RE.match(row.email):
            errors.append("Email does not look valid")
        if not row.email:
            warnings.append("No email, so invoices cannot be emailed to this customer yet")
        if not row.address:
            warnings.append("No address, so the customer is added without a property")
        if errors:
            errs += 1
            results.append(ImportRowResult(**row.model_dump(), status="error",
                                           warnings=warnings, errors=errors))
            continue
        key = ("e", row.email) if row.email else ("n", row.name.strip().lower())
        norm = normalize_address(row.address)
        customer = by_key.get(key)
        if customer is not None or key in by_key:
            if not row.address or (key, norm) in seen_props:
                status = "duplicate"
                skipped += 1
            else:
                status = "new_property"
                created_p += 1
        else:
            status = "new"
            created_c += 1
            if row.address:
                created_p += 1
        if apply and status != "duplicate":
            if status == "new":
                customer = Customer(account_id=account.id, name=row.name.strip(), email=row.email,
                                    phone=row.phone, billing_address=row.billing_address, notes="")
                db.add(customer)
                db.flush()
                by_key[key] = customer
            if row.address:
                db.add(Property(account_id=account.id, customer_id=customer.id, address=row.address,
                                address_norm=norm, lot_size_sqft=row.lot_size_sqft,
                                billing_mode=row.billing_mode, monthly_rate=row.monthly_rate,
                                per_visit_price=row.per_visit_price, notes=row.notes))
        if status != "duplicate" and key not in by_key:
            by_key[key] = None  # placeholder so later rows in this file match it
        if row.address:
            seen_props.add((key, norm))
        results.append(ImportRowResult(**row.model_dump(), status=status, warnings=warnings))
    return results, {"customers_created": created_c, "properties_created": created_p,
                     "skipped_duplicates": skipped, "errors": errs}


@router.get("/template", response_class=PlainTextResponse)
def template(account: Account = Depends(current_account)):
    return PlainTextResponse(TEMPLATE, media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="customers-template.csv"'})


@router.post("/preview", response_model=ImportPreview)
async def preview(file: UploadFile = File(...), account: Account = Depends(current_account),
                  db: Session = Depends(get_db)):
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(400, "File is larger than 2 MB")
    rows, broken = parse_csv(raw)
    results, counts = process(rows, db, account, apply=False)
    results = sorted(results + broken, key=lambda r: r.line)
    counts["errors"] += len(broken)
    return ImportPreview(rows=results, counts=counts)


@router.post("/commit", response_model=ImportCommitResult)
def commit(body: ImportCommit, account: Account = Depends(current_account),
           db: Session = Depends(get_db)):
    if len(body.rows) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (limit {MAX_ROWS})")
    _, counts = process(body.rows, db, account, apply=True)
    db.commit()
    return ImportCommitResult(**counts)
