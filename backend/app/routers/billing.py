from datetime import date
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Company, Contract, MonthlyBilling
from ..services import tariff as tariff_svc
from ..services.holiday_calc import last_day_of_month, month_abbr
from ..services.excel_gen import generate_recaudo, generate_credito

router = APIRouter(prefix="/billing", tags=["billing"])
templates = Jinja2Templates(directory="app/templates")


def _active_companies(db: Session) -> list[Company]:
    return (
        db.query(Company)
        .options(joinedload(Company.contracts).joinedload(Contract.spaces))
        .join(Contract, (Contract.company_id == Company.id) & Contract.is_active)
        .order_by(Company.name)
        .all()
    )


@router.get("/", response_class=HTMLResponse)
def billing_page(
    request: Request,
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
):
    today = date.today()
    # Default: bill for next month
    if not month or not year:
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        month, year = next_month, next_year

    companies = _active_companies(db)
    preview_rows = []
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    payment_deadline = last_day_of_month(prev_year, prev_month, db)

    for company in companies:
        try:
            calc = tariff_svc.get_billing_calc(company, year, month, db)
        except Exception as e:
            calc = {"error": str(e)}

        existing = db.query(MonthlyBilling).filter(
            MonthlyBilling.company_id == company.id,
            MonthlyBilling.billing_month == month,
            MonthlyBilling.billing_year == year,
        ).first()

        preview_rows.append({
            "company": company,
            "calc": calc,
            "existing_billing": existing,
            "contract": company.active_contract,
        })

    return templates.TemplateResponse(
        "billing/generate.html",
        {
            "request": request,
            "month": month,
            "year": year,
            "month_abbr": month_abbr(month),
            "preview_rows": preview_rows,
            "payment_deadline": payment_deadline,
            "has_existing": any(r["existing_billing"] for r in preview_rows),
        },
    )


@router.post("/generate")
def generate_billing(
    month: int = Form(...),
    year: int = Form(...),
    overwrite: str = Form("no"),
    db: Session = Depends(get_db),
):
    companies = _active_companies(db)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    payment_deadline = last_day_of_month(prev_year, prev_month, db)

    saved_billings: dict[int, MonthlyBilling] = {}

    for company in companies:
        try:
            calc = tariff_svc.get_billing_calc(company, year, month, db)
        except Exception:
            continue
        if calc.get("is_over_limit"):
            continue

        existing = db.query(MonthlyBilling).filter(
            MonthlyBilling.company_id == company.id,
            MonthlyBilling.billing_month == month,
            MonthlyBilling.billing_year == year,
        ).first()

        if existing and overwrite != "si":
            saved_billings[company.id] = existing
            continue

        if existing:
            existing.daily_rate_without_iva = calc["daily_rate_without_iva"]
            existing.subtotal_without_iva = calc["subtotal_without_iva"]
            existing.total_with_iva = calc["total_with_iva"]
            existing.payment_deadline = payment_deadline
            billing = existing
        else:
            billing = MonthlyBilling(
                company_id=company.id,
                billing_month=month,
                billing_year=year,
                days_count=30,
                daily_rate_without_iva=calc["daily_rate_without_iva"],
                subtotal_without_iva=calc["subtotal_without_iva"],
                total_with_iva=calc["total_with_iva"],
                payment_deadline=payment_deadline,
                status="pendiente",
            )
            db.add(billing)

        db.flush()
        saved_billings[company.id] = billing

    db.commit()
    return RedirectResponse(f"/billing/download?month={month}&year={year}", status_code=303)


@router.get("/download")
def download_billing(
    month: int,
    year: int,
    file_type: str = "recaudo",
    db: Session = Depends(get_db),
):
    companies = _active_companies(db)
    billings_rows = db.query(MonthlyBilling).filter(
        MonthlyBilling.billing_month == month,
        MonthlyBilling.billing_year == year,
    ).all()
    billings_map = {b.company_id: b for b in billings_rows}

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    payment_deadline = last_day_of_month(prev_year, prev_month, db)

    regular = [c for c in companies if not c.is_fondo_emprender]
    fondo = [c for c in companies if c.is_fondo_emprender]

    mes = month_abbr(month)

    if file_type == "credito":
        content = generate_credito(fondo, billings_map, month, year)
        filename = f"facturacion-credito-{mes}{year}.xlsx"
    else:
        content = generate_recaudo(regular, billings_map, month, year, payment_deadline)
        filename = f"orden-recaudo-{mes}{year}.xlsx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history", response_class=HTMLResponse)
def billing_history(request: Request, db: Session = Depends(get_db)):
    billings = (
        db.query(MonthlyBilling)
        .options(joinedload(MonthlyBilling.company))
        .order_by(MonthlyBilling.billing_year.desc(), MonthlyBilling.billing_month.desc())
        .all()
    )
    # Group by month/year
    grouped: dict[tuple, list] = {}
    for b in billings:
        key = (b.billing_year, b.billing_month)
        grouped.setdefault(key, []).append(b)

    periods = [
        {
            "year": k[0],
            "month": k[1],
            "month_abbr": month_abbr(k[1]),
            "billings": v,
            "total": sum(float(b.total_with_iva or 0) for b in v),
            "paid": sum(1 for b in v if b.status == "pagado"),
            "pending": sum(1 for b in v if b.status == "pendiente"),
        }
        for k, v in sorted(grouped.items(), reverse=True)
    ]
    return templates.TemplateResponse(
        "billing/history.html", {"request": request, "periods": periods}
    )
