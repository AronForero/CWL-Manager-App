from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from .database import Base, engine, get_db
from .models import Company, Contract, MonthlyBilling, TariffRate
from .routers import billing, companies, payments
from .services import tariff as tariff_svc
from .services.holiday_calc import month_abbr, seed_holidays

app = FastAPI(title="Coworking Labs", docs_url=None, redoc_url=None)

templates = Jinja2Templates(directory="app/templates")


def _seed_tariffs(db: Session):
    rates = [
        ("A", 1, 250879), ("A", 2, 376319), ("A", 3, 501759),
        ("B", 1, 430079), ("B", 2, 645118), ("B", 3, 860158),
        ("C", 1, 1003517), ("C", 2, 1505276), ("C", 3, 2007035),
        ("D", 1, 1003517), ("D", 2, 1505276), ("D", 3, 2007035),
    ]
    for space_type, year_number, rate in rates:
        existing = db.query(TariffRate).filter(
            TariffRate.space_type == space_type,
            TariffRate.year_number == year_number,
        ).first()
        if not existing:
            db.add(TariffRate(space_type=space_type, year_number=year_number, monthly_rate_with_iva=rate))
    db.commit()


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        _seed_tariffs(db)
        seed_holidays(db, from_year=2025, to_year=2030)
    finally:
        db.close()


app.include_router(companies.router)
app.include_router(billing.router)
app.include_router(payments.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    from datetime import date
    today = date.today()
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1

    companies = (
        db.query(Company)
        .options(joinedload(Company.contracts).joinedload(Contract.spaces))
        .all()
    )

    active_companies = [c for c in companies if c.active_contract]
    near_limit = []
    active_rows = []
    for c in active_companies:
        contract = c.active_contract
        total_months = tariff_svc.months_active_total(c)
        tier = tariff_svc._tier_for_months(total_months - 1) if total_months > 0 else 1
        remaining = tariff_svc.months_remaining(c)
        if 0 < remaining <= 6:
            near_limit.append({"company": c, "remaining": remaining})
        active_rows.append({
            "company": c,
            "contract": contract,
            "spaces": contract.active_spaces if contract else [],
            "total_months": total_months,
            "tier": tier,
            "remaining_months": remaining,
            "near_limit": 0 < remaining <= 6,
            "over_limit": remaining == 0 and total_months >= tariff_svc.MAX_MONTHS,
        })
    active_rows.sort(
        key=lambda r: r["contract"].start_date if r["contract"] else date.min,
        reverse=True,
    )

    billing_this_month = db.query(MonthlyBilling).filter(
        MonthlyBilling.billing_month == next_month,
        MonthlyBilling.billing_year == next_year,
    ).all()

    status_counts = {"pendiente": 0, "pagado": 0, "revisar": 0}
    for b in billing_this_month:
        status_counts[b.status] = status_counts.get(b.status, 0) + 1

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_active": len(active_companies),
            "total_companies": len(companies),
            "next_month": next_month,
            "next_year": next_year,
            "next_month_abbr": month_abbr(next_month),
            "billing_generated": len(billing_this_month) > 0,
            "billing_count": len(billing_this_month),
            "status_counts": status_counts,
            "near_limit": near_limit,
            "active_rows": active_rows,
        },
    )
