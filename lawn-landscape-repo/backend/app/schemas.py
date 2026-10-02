from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BillingMode = Literal["monthly_flat", "per_visit"]


class PropertyIn(BaseModel):
    address: str = Field(min_length=3, max_length=300)
    geofence_radius_m: int = Field(default=75, ge=10, le=1000)
    lot_size_sqft: int | None = Field(default=None, ge=0)
    mow_frequency: str = "weekly"
    billing_mode: BillingMode = "monthly_flat"
    monthly_rate: float | None = Field(default=None, ge=0)
    per_visit_price: float | None = Field(default=None, ge=0)
    notes: str = ""


class PropertyOut(PropertyIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    lat: float | None = None
    lng: float | None = None


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=50)
    billing_address: str = Field(default="", max_length=300)
    notes: str = ""
    active: bool = True
    properties: list[PropertyIn] = []


class CustomerUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=50)
    billing_address: str = Field(default="", max_length=300)
    notes: str = ""
    active: bool = True


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    phone: str
    billing_address: str
    notes: str
    active: bool
    properties: list[PropertyOut] = []


class CustomerSummary(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    active: bool
    property_count: int
    first_address: str


class LoginIn(BaseModel):
    password: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_name: str = ""
    timezone: str = "America/Chicago"
    base_address: str
    base_lat: float | None
    base_lng: float | None
    rate_per_1000_sqft: float
    travel_charge_per_minute: float
    min_visit_price: float
    tax_rate_percent: float
    late_fee_type: Literal["flat", "percent"]
    late_fee_value: float
    late_fee_grace_days: int
    gmail_address: str
    gmail_password_set: bool = False


class SettingsIn(BaseModel):
    business_name: str = Field(default="", max_length=200)
    timezone: str = "America/Chicago"
    base_address: str = ""
    rate_per_1000_sqft: float = Field(default=0, ge=0)
    travel_charge_per_minute: float = Field(default=0, ge=0)
    min_visit_price: float = Field(default=0, ge=0)
    tax_rate_percent: float = Field(default=0, ge=0, le=30)
    late_fee_type: Literal["flat", "percent"] = "flat"
    late_fee_value: float = Field(default=0, ge=0)
    late_fee_grace_days: int = Field(default=30, ge=0, le=365)
    gmail_address: str = ""
    # None = leave the saved password alone; "" = clear it; text = replace it.
    gmail_app_password: str | None = None


class ImportRow(BaseModel):
    line: int
    name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    billing_address: str = ""
    lot_size_sqft: int | None = None
    billing_mode: BillingMode = "monthly_flat"
    monthly_rate: float | None = None
    per_visit_price: float | None = None
    notes: str = ""


class ImportRowResult(ImportRow):
    status: Literal["new", "new_property", "duplicate", "error"]
    warnings: list[str] = []
    errors: list[str] = []


class ImportPreview(BaseModel):
    rows: list[ImportRowResult]
    counts: dict[str, int]


class ImportCommit(BaseModel):
    rows: list[ImportRow]


class ImportCommitResult(BaseModel):
    customers_created: int
    properties_created: int
    skipped_duplicates: int
    errors: int
