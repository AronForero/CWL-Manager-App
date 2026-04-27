from datetime import date
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Company, Contract, ContractSpace
from ..services import tariff as tariff_svc

router = APIRouter(prefix="/companies", tags=["companies"])
templates = Jinja2Templates(directory="app/templates")


def _load_company(company_id: int, db: Session) -> Company:
    company = (
        db.query(Company)
        .options(joinedload(Company.contracts).joinedload(Contract.spaces))
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


@router.get("/", response_class=HTMLResponse)
def list_companies(request: Request, db: Session = Depends(get_db)):
    companies = (
        db.query(Company)
        .options(joinedload(Company.contracts).joinedload(Contract.spaces))
        .order_by(Company.name)
        .all()
    )
    rows = []
    for c in companies:
        contract = c.active_contract
        total_months = tariff_svc.months_active_total(c)
        tier = tariff_svc._tier_for_months(total_months - 1) if total_months > 0 else 1
        remaining = tariff_svc.months_remaining(c)
        rows.append({
            "company": c,
            "contract": contract,
            "spaces": contract.active_spaces if contract else [],
            "total_months": total_months,
            "tier": tier,
            "remaining_months": remaining,
            "near_limit": remaining <= 6 and remaining > 0,
            "over_limit": remaining == 0 and total_months >= tariff_svc.MAX_MONTHS,
        })
    return templates.TemplateResponse(
        "companies/list.html", {"request": request, "rows": rows}
    )


@router.get("/new", response_class=HTMLResponse)
def new_company_form(request: Request):
    return templates.TemplateResponse(
        "companies/form.html", {"request": request, "company": None, "errors": []}
    )


@router.post("/new")
def create_company(
    request: Request,
    name: str = Form(...),
    nit: str = Form(...),
    billing_email: str = Form(""),
    address: str = Form(""),
    is_affiliated: str = Form("no"),
    is_fondo_emprender: str = Form("no"),
    fondo_emprender_ref: str = Form(""),
    ceco: str = Form(...),
    contract_number: str = Form(""),
    start_date: str = Form(...),
    db: Session = Depends(get_db),
):
    errors = []
    existing = db.query(Company).filter(Company.nit == nit.strip()).first()
    if existing:
        errors.append(f"Ya existe una empresa con NIT {nit}")

    if errors:
        return templates.TemplateResponse(
            "companies/form.html", {"request": request, "company": None, "errors": errors}
        )

    company = Company(
        name=name.strip(),
        nit=nit.strip(),
        billing_email=billing_email.strip() or None,
        address=address.strip() or None,
        is_affiliated=(is_affiliated == "si"),
        is_fondo_emprender=(is_fondo_emprender == "si"),
        fondo_emprender_ref=int(fondo_emprender_ref) if fondo_emprender_ref.strip() else None,
    )
    db.add(company)
    db.flush()

    parsed_start = date.fromisoformat(start_date)
    contract = Contract(
        company_id=company.id,
        contract_number=contract_number.strip() or None,
        ceco=ceco.strip(),
        start_date=parsed_start,
        is_active=True,
    )
    db.add(contract)
    db.commit()
    return RedirectResponse(f"/companies/{company.id}", status_code=303)


@router.get("/{company_id}", response_class=HTMLResponse)
def company_detail(company_id: int, request: Request, db: Session = Depends(get_db)):
    company = _load_company(company_id, db)
    contract = company.active_contract
    total_months = tariff_svc.months_active_total(company)
    tier = tariff_svc._tier_for_months(total_months - 1) if total_months > 0 else 1
    remaining = tariff_svc.months_remaining(company)
    billings = sorted(company.billings, key=lambda b: (b.billing_year, b.billing_month), reverse=True)
    return templates.TemplateResponse(
        "companies/detail.html",
        {
            "request": request,
            "company": company,
            "contract": contract,
            "spaces": contract.active_spaces if contract else [],
            "all_spaces": contract.spaces if contract else [],
            "billings": billings,
            "total_months": total_months,
            "tier": tier,
            "remaining_months": remaining,
        },
    )


@router.get("/{company_id}/edit", response_class=HTMLResponse)
def edit_company_form(company_id: int, request: Request, db: Session = Depends(get_db)):
    company = _load_company(company_id, db)
    return templates.TemplateResponse(
        "companies/form.html", {"request": request, "company": company, "errors": []}
    )


@router.post("/{company_id}/edit")
def update_company(
    company_id: int,
    request: Request,
    name: str = Form(...),
    billing_email: str = Form(""),
    address: str = Form(""),
    is_affiliated: str = Form("no"),
    is_fondo_emprender: str = Form("no"),
    fondo_emprender_ref: str = Form(""),
    db: Session = Depends(get_db),
):
    company = _load_company(company_id, db)
    company.name = name.strip()
    company.billing_email = billing_email.strip() or None
    company.address = address.strip() or None
    company.is_affiliated = (is_affiliated == "si")
    company.is_fondo_emprender = (is_fondo_emprender == "si")
    company.fondo_emprender_ref = int(fondo_emprender_ref) if fondo_emprender_ref.strip() else None
    db.commit()
    return RedirectResponse(f"/companies/{company_id}", status_code=303)


@router.post("/{company_id}/spaces/add")
def add_space(
    company_id: int,
    space_type: str = Form(...),
    quantity: int = Form(...),
    start_date: str = Form(...),
    db: Session = Depends(get_db),
):
    company = _load_company(company_id, db)
    contract = company.active_contract
    if not contract:
        raise HTTPException(status_code=400, detail="La empresa no tiene contrato activo")
    space = ContractSpace(
        contract_id=contract.id,
        space_type=space_type.upper(),
        quantity=quantity,
        start_date=date.fromisoformat(start_date),
        is_active=True,
    )
    db.add(space)
    db.commit()
    return RedirectResponse(f"/companies/{company_id}", status_code=303)


@router.post("/{company_id}/spaces/{space_id}/remove")
def remove_space(
    company_id: int,
    space_id: int,
    end_date: str = Form(None),
    db: Session = Depends(get_db),
):
    space = db.query(ContractSpace).filter(ContractSpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    space.is_active = False
    space.end_date = date.fromisoformat(end_date) if end_date else date.today()
    db.commit()
    return RedirectResponse(f"/companies/{company_id}", status_code=303)


@router.post("/{company_id}/deactivate")
def deactivate_company(
    company_id: int,
    end_date: str = Form(None),
    db: Session = Depends(get_db),
):
    company = _load_company(company_id, db)
    contract = company.active_contract
    if contract:
        contract.is_active = False
        contract.end_date = date.fromisoformat(end_date) if end_date else date.today()
        for space in contract.active_spaces:
            space.is_active = False
            space.end_date = contract.end_date
    db.commit()
    return RedirectResponse(f"/companies/{company_id}", status_code=303)


@router.post("/{company_id}/reactivate")
def reactivate_company(
    company_id: int,
    ceco: str = Form(...),
    contract_number: str = Form(""),
    start_date: str = Form(...),
    db: Session = Depends(get_db),
):
    company = _load_company(company_id, db)
    contract = Contract(
        company_id=company.id,
        contract_number=contract_number.strip() or None,
        ceco=ceco.strip(),
        start_date=date.fromisoformat(start_date),
        is_active=True,
    )
    db.add(contract)
    db.commit()
    return RedirectResponse(f"/companies/{company_id}", status_code=303)
