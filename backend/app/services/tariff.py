from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from ..models import Company, TariffRate

IVA = Decimal("1.19")
DAYS = 30
MAX_MONTHS = 60  # 5-year limit


def _total_active_months_before(company: Company, billing_year: int, billing_month: int) -> int:
    """
    Sum the number of calendar months the company was active across all contracts,
    counting only months that started before the billing month/year.
    """
    target = date(billing_year, billing_month, 1)
    total = 0
    for contract in company.contracts:
        start = contract.start_date
        end = contract.end_date or date.today()
        # Count months from start up to (not including) the billing month
        effective_end = min(end, target)
        if effective_end <= start:
            continue
        delta = relativedelta(effective_end, start)
        months = delta.years * 12 + delta.months
        total += months
    return total


def _tier_for_months(total_months: int) -> int:
    """Return tier year (1, 2, or 3) given accumulated months active."""
    if total_months < 12:
        return 1
    if total_months < 24:
        return 2
    return 3


def get_tariff_rate(space_type: str, tier: int, db: Session) -> Decimal:
    rate = db.query(TariffRate).filter(
        TariffRate.space_type == space_type,
        TariffRate.year_number == tier,
    ).first()
    if not rate:
        raise ValueError(f"No tariff rate found for type {space_type} year {tier}")
    return Decimal(str(rate.monthly_rate_with_iva))


def get_billing_calc(company: Company, billing_year: int, billing_month: int, db: Session) -> dict:
    """
    Return billing breakdown for a company for the given month/year.
    Handles tier transitions mid-month using a blended approach.

    Returns:
        {
            "subtotal_without_iva": Decimal,
            "daily_rate_without_iva": Decimal,   # subtotal / 30
            "total_with_iva": Decimal,
            "tier": int,                          # dominant tier for the month
            "is_transition_month": bool,
            "is_over_limit": bool,
        }
    """
    active_contract = company.active_contract
    if not active_contract:
        raise ValueError(f"Company {company.name} has no active contract")

    months_before = _total_active_months_before(company, billing_year, billing_month)

    if months_before >= MAX_MONTHS:
        return {"is_over_limit": True}

    tier_start = _tier_for_months(months_before)
    tier_end = _tier_for_months(months_before + 1)
    is_transition = tier_start != tier_end

    # Find the tier transition date within the billing month
    # It occurs when the company reaches a tier boundary (month 12 or 24)
    transition_date = None
    if is_transition:
        boundary = 12 if tier_start == 1 else 24
        months_into_contract = boundary - _total_active_months_before(company, active_contract.start_date.year, active_contract.start_date.month)
        transition_date = active_contract.start_date + relativedelta(months=months_into_contract)

    active_spaces = active_contract.active_spaces
    subtotal = Decimal("0")

    for space in active_spaces:
        if is_transition and transition_date:
            days_old = transition_date.day - 1
            days_new = DAYS - days_old
            rate_old = get_tariff_rate(space.space_type, tier_start, db)
            rate_new = get_tariff_rate(space.space_type, tier_end, db)
            daily_old = (rate_old / IVA) / DAYS
            daily_new = (rate_new / IVA) / DAYS
            subtotal += (daily_old * days_old + daily_new * days_new) * space.quantity
        else:
            rate = get_tariff_rate(space.space_type, tier_start, db)
            subtotal += (rate / IVA) * space.quantity

    subtotal = subtotal.quantize(Decimal("0.01"))
    daily_rate = (subtotal / DAYS).quantize(Decimal("0.0001"))
    total = (subtotal * IVA).quantize(Decimal("0.01"))

    return {
        "subtotal_without_iva": subtotal,
        "daily_rate_without_iva": daily_rate,
        "total_with_iva": total,
        "tier": tier_start,
        "is_transition_month": is_transition,
        "is_over_limit": False,
    }


def months_active_total(company: Company) -> int:
    """Current total active months for the company (to today)."""
    today = date.today()
    return _total_active_months_before(company, today.year, today.month) + (
        1 if any(c.is_active for c in company.contracts) else 0
    )


def months_remaining(company: Company) -> int:
    return max(0, MAX_MONTHS - months_active_total(company))
