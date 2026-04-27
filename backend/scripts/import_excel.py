"""
One-time script to bootstrap the database from CONTROL-GENERAL-2026.xlsx.
Run inside the Docker container:
  docker compose exec app python scripts/import_excel.py
Or locally (with DATABASE_URL set):
  python backend/scripts/import_excel.py
"""
import os
import sys
from datetime import date

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://moni:changeme@localhost:5432/monifacturas")
EXCEL_PATH = os.environ.get("EXCEL_PATH", "/app/guias-excel/CONTROL-GENERAL-2026.xlsx")

# Fallback for local runs
if not os.path.exists(EXCEL_PATH):
    EXCEL_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "guias-excel", "CONTROL-GENERAL-2026.xlsx"
    )

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

from app.database import Base
from app.models import Company, Contract, ContractSpace, TariffRate, ColombianHoliday

FONDO_EMPRENDER_NITS = {"901943456"}  # PIXEL CAP — identified from facturacion-credito.xlsx

FONDO_EMPRENDER_REFS = {"901943456": 104001}


def _clean_ceco(raw: str) -> str:
    if not raw:
        return ""
    raw = str(raw).strip()
    if "(" in raw:
        raw = raw[:raw.index("(")].strip()
    return raw


def _clean_nit(raw) -> str:
    if raw is None:
        return ""
    return str(raw).strip().replace("\xa0", "").replace(" ", "")


def _parse_spaces(space_type_raw, quantity_raw) -> list[tuple[str, int]]:
    """Handle cases like 'C | B' with '1 | 1'."""
    if space_type_raw is None:
        return []
    types = [s.strip() for s in str(space_type_raw).split("|")]
    quantities_raw = str(quantity_raw) if quantity_raw is not None else "1"
    quantities = [q.strip() for q in quantities_raw.split("|")]
    result = []
    for i, t in enumerate(types):
        qty_str = quantities[i] if i < len(quantities) else "1"
        try:
            qty = int(float(qty_str))
        except ValueError:
            qty = 1
        if t and t.upper() in ("A", "B", "C", "D"):
            result.append((t.upper(), qty))
    return result


def _seed_tariffs(db):
    rates = [
        ("A", 1, 250879), ("A", 2, 376319), ("A", 3, 501759),
        ("B", 1, 430079), ("B", 2, 645118), ("B", 3, 860158),
        ("C", 1, 1003517), ("C", 2, 1505276), ("C", 3, 2007035),
        ("D", 1, 1003517), ("D", 2, 1505276), ("D", 3, 2007035),
    ]
    for space_type, year_number, rate in rates:
        if not db.query(TariffRate).filter(
            TariffRate.space_type == space_type,
            TariffRate.year_number == year_number
        ).first():
            db.add(TariffRate(space_type=space_type, year_number=year_number, monthly_rate_with_iva=rate))
    db.commit()
    print("  Tarifas: OK")


def _seed_holidays(db):
    from app.services.holiday_calc import seed_holidays
    added = seed_holidays(db, from_year=2025, to_year=2030)
    print(f"  Festivos: {added} agregados")


def import_companies(db):
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb["Control Pagos-2026"]

    # Headers are at row 3, data starts at row 4
    created = 0
    skipped = 0

    for row in ws.iter_rows(min_row=4, values_only=True):
        row_num = row[0]
        name = row[1]

        if not name or not str(name).strip():
            continue

        nit_raw = row[2]
        contract_num_raw = row[3]
        ceco_raw = row[4]
        email_raw = row[5]
        space_type_raw = row[7]
        quantity_raw = row[8]
        start_date_raw = row[10]

        nit = _clean_nit(nit_raw)
        clean_ceco = _clean_ceco(str(ceco_raw) if ceco_raw else "")
        name = str(name).strip()

        if not nit or not clean_ceco:
            print(f"  SKIP row #{row_num} ({name}): falta NIT o CECO")
            skipped += 1
            continue

        # Parse start date
        if isinstance(start_date_raw, (date,)):
            start_date = start_date_raw
        elif hasattr(start_date_raw, 'date'):
            start_date = start_date_raw.date()
        elif start_date_raw:
            from dateutil.parser import parse as parse_date
            start_date = parse_date(str(start_date_raw)).date()
        else:
            print(f"  SKIP row #{row_num} ({name}): sin fecha de inicio")
            skipped += 1
            continue

        # Parse emails (some have multiple separated by ;)
        billing_email = None
        if email_raw:
            emails = [e.strip() for e in str(email_raw).replace("\xa0", "").split(";") if e.strip()]
            billing_email = emails[0] if emails else None

        # Check fondo emprender
        is_fe = nit in FONDO_EMPRENDER_NITS
        fe_ref = FONDO_EMPRENDER_REFS.get(nit)

        # Parse contract number
        contract_number = None
        if contract_num_raw:
            try:
                contract_number = str(int(float(str(contract_num_raw))))
            except (ValueError, TypeError):
                contract_number = str(contract_num_raw).strip()

        # Upsert company
        existing_company = db.query(Company).filter(Company.nit == nit).first()
        if existing_company:
            print(f"  YA EXISTE: {name} (NIT {nit}) — skip")
            skipped += 1
            continue

        company = Company(
            name=name,
            nit=nit,
            billing_email=billing_email,
            is_affiliated=False,  # default; update via UI
            is_fondo_emprender=is_fe,
            fondo_emprender_ref=fe_ref,
        )
        db.add(company)
        db.flush()

        # Check if CECO already exists (shouldn't, but guard)
        existing_contract = db.query(Contract).filter(Contract.ceco == clean_ceco).first()
        if existing_contract:
            print(f"  CECO {clean_ceco} ya existe — skip contrato")
        else:
            contract = Contract(
                company_id=company.id,
                contract_number=contract_number,
                ceco=clean_ceco,
                start_date=start_date,
                is_active=True,
            )
            db.add(contract)
            db.flush()

            spaces = _parse_spaces(space_type_raw, quantity_raw)
            for space_type, qty in spaces:
                db.add(ContractSpace(
                    contract_id=contract.id,
                    space_type=space_type,
                    quantity=qty,
                    start_date=start_date,
                    is_active=True,
                ))

        db.commit()
        print(f"  ✓ {name} (NIT {nit}) — {clean_ceco} — espacios: {_parse_spaces(space_type_raw, quantity_raw)}")
        created += 1

    print(f"\nResumen: {created} empresas importadas, {skipped} omitidas.")


def main():
    print("Creando tablas...")
    Base.metadata.create_all(bind=engine)

    db = Session()
    try:
        print("\nSembrando tarifas y festivos...")
        _seed_tariffs(db)
        _seed_holidays(db)

        print(f"\nImportando desde: {EXCEL_PATH}")
        import_companies(db)

        print("\n✅ Importación completa.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
