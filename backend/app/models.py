from datetime import date, datetime
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class TariffRate(Base):
    __tablename__ = "tariff_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    space_type: Mapped[str] = mapped_column(String(1), nullable=False)
    year_number: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_rate_with_iva: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    billing_email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    is_affiliated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_fondo_emprender: Mapped[bool] = mapped_column(Boolean, default=False)
    fondo_emprender_ref: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    contracts: Mapped[list["Contract"]] = relationship(
        "Contract", back_populates="company", cascade="all, delete-orphan"
    )
    billings: Mapped[list["MonthlyBilling"]] = relationship(
        "MonthlyBilling", back_populates="company", cascade="all, delete-orphan"
    )

    @property
    def active_contract(self) -> "Contract | None":
        return next((c for c in self.contracts if c.is_active), None)


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    contract_number: Mapped[str | None] = mapped_column(String(50))
    ceco: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped["Company"] = relationship("Company", back_populates="contracts")
    spaces: Mapped[list["ContractSpace"]] = relationship(
        "ContractSpace", back_populates="contract", cascade="all, delete-orphan"
    )

    @property
    def active_spaces(self) -> list["ContractSpace"]:
        return [s for s in self.spaces if s.is_active]


class ContractSpace(Base):
    __tablename__ = "contract_spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )
    space_type: Mapped[str] = mapped_column(String(1), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    contract: Mapped["Contract"] = relationship("Contract", back_populates="spaces")


class MonthlyBilling(Base):
    __tablename__ = "monthly_billings"
    __table_args__ = (
        UniqueConstraint("company_id", "billing_month", "billing_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False
    )
    billing_month: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_year: Mapped[int] = mapped_column(Integer, nullable=False)
    days_count: Mapped[int] = mapped_column(Integer, default=30)
    daily_rate_without_iva: Mapped[float | None] = mapped_column(Numeric(14, 4))
    subtotal_without_iva: Mapped[float | None] = mapped_column(Numeric(12, 2))
    total_with_iva: Mapped[float | None] = mapped_column(Numeric(12, 2))
    payment_deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pendiente")
    order_reference: Mapped[str | None] = mapped_column(String(50))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped["Company"] = relationship("Company", back_populates="billings")


class ColombianHoliday(Base):
    __tablename__ = "colombian_holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holiday_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(100))
