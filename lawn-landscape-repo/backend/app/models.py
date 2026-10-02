from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String,
                        Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Chicago")
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Settings(Base):
    """One row per account. Quote and invoice math will read only from here."""
    __tablename__ = "settings"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    base_address: Mapped[str] = mapped_column(String(300), default="")
    base_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    base_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    rate_per_1000_sqft: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    travel_charge_per_minute: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    min_visit_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    tax_rate_percent: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    late_fee_type: Mapped[str] = mapped_column(String(10), default="flat")  # flat | percent
    late_fee_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    late_fee_grace_days: Mapped[int] = mapped_column(Integer, default=30)
    gmail_address: Mapped[str] = mapped_column(String(200), default="")
    gmail_app_password_enc: Mapped[str] = mapped_column(Text, default="")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), default="", index=True)
    phone: Mapped[str] = mapped_column(String(50), default="")
    billing_address: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    properties: Mapped[list["Property"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan", order_by="Property.id")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    address: Mapped[str] = mapped_column(String(300))
    address_norm: Mapped[str] = mapped_column(String(300), index=True)
    # Filled in by the geocoder in phase 2.
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    geofence_radius_m: Mapped[int] = mapped_column(Integer, default=75)
    lot_size_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mow_frequency: Mapped[str] = mapped_column(String(30), default="weekly")
    billing_mode: Mapped[str] = mapped_column(String(20), default="monthly_flat")  # monthly_flat | per_visit
    monthly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    per_visit_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    customer: Mapped[Customer] = relationship(back_populates="properties")
