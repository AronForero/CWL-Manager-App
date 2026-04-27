import calendar
from datetime import date, timedelta
import holidays as holidays_lib
from sqlalchemy.orm import Session
from ..models import ColombianHoliday

MONTH_ABBR_ES = {
    1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC",
}

MONTH_NAME_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def _get_holiday_dates(db: Session) -> set[date]:
    rows = db.query(ColombianHoliday).all()
    return {r.holiday_date for r in rows}


def last_day_of_month(year: int, month: int, db: Session) -> date:
    """Return the last working day of the given month.
    If the last calendar day is a weekend or Colombian holiday, walk backwards."""
    holiday_dates = _get_holiday_dates(db)
    last_day = calendar.monthrange(year, month)[1]
    current = date(year, month, last_day)
    while current.weekday() >= 5 or current in holiday_dates:
        current -= timedelta(days=1)
    return current


def third_business_day(year: int, month: int, db: Session) -> date:
    """Return the 3rd business day of the given month (skip weekends and Colombian holidays)."""
    holiday_dates = _get_holiday_dates(db)
    current = date(year, month, 1)
    count = 0
    while True:
        if current.weekday() < 5 and current not in holiday_dates:
            count += 1
            if count == 3:
                return current
        current += timedelta(days=1)


def seed_holidays(db: Session, from_year: int = 2025, to_year: int = 2030) -> int:
    """Populate colombian_holidays table for the given year range."""
    added = 0
    for year in range(from_year, to_year + 1):
        co_holidays = holidays_lib.Colombia(years=year)
        for h_date, h_name in co_holidays.items():
            existing = db.query(ColombianHoliday).filter(
                ColombianHoliday.holiday_date == h_date
            ).first()
            if not existing:
                db.add(ColombianHoliday(holiday_date=h_date, description=h_name[:100]))
                added += 1
    db.commit()
    return added


def month_abbr(month: int) -> str:
    return MONTH_ABBR_ES[month]


def month_name(month: int) -> str:
    return MONTH_NAME_ES[month]
