from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MonthlyBilling

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{billing_id}/mark-paid")
def mark_paid(
    billing_id: int,
    order_reference: str = Form(""),
    redirect_to: str = Form("/billing/history"),
    db: Session = Depends(get_db),
):
    billing = db.query(MonthlyBilling).filter(MonthlyBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Facturación no encontrada")
    billing.status = "pagado"
    billing.order_reference = order_reference.strip() or None
    db.commit()
    return RedirectResponse(redirect_to, status_code=303)


@router.post("/{billing_id}/mark-review")
def mark_review(
    billing_id: int,
    redirect_to: str = Form("/billing/history"),
    db: Session = Depends(get_db),
):
    billing = db.query(MonthlyBilling).filter(MonthlyBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Facturación no encontrada")
    billing.status = "revisar"
    db.commit()
    return RedirectResponse(redirect_to, status_code=303)


@router.post("/{billing_id}/mark-pending")
def mark_pending(
    billing_id: int,
    redirect_to: str = Form("/billing/history"),
    db: Session = Depends(get_db),
):
    billing = db.query(MonthlyBilling).filter(MonthlyBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Facturación no encontrada")
    billing.status = "pendiente"
    db.commit()
    return RedirectResponse(redirect_to, status_code=303)
