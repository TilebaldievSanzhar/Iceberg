from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import User, Bank
from app.schemas import BankResponse

router = APIRouter()


@router.get("", response_model=List[BankResponse])
def get_banks(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get list of supported banks."""
    banks = db.query(Bank).order_by(Bank.name).all()
    return banks
