from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user
from app.models import User, Account, Bank
from app.schemas import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter()


@router.get("", response_model=List[AccountResponse])
def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all accounts for current user."""
    accounts = (
        db.query(Account)
        .options(joinedload(Account.bank))
        .filter(Account.user_id == current_user.id)
        .order_by(Account.created_at.desc())
        .all()
    )
    return accounts


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new account."""
    # Verify bank exists
    bank = db.query(Bank).filter(Bank.id == account_data.bank_id).first()
    if not bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank not found",
        )

    account = Account(
        user_id=current_user.id,
        bank_id=account_data.bank_id,
        name=account_data.name,
        currency=account_data.currency,
        account_number=account_data.account_number,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    # Load bank relationship
    db.refresh(account, ["bank"])
    return account


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get account by ID."""
    account = (
        db.query(Account)
        .options(joinedload(Account.bank))
        .filter(Account.id == account_id, Account.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: UUID,
    account_data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update account."""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id,
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    if account_data.name is not None:
        account.name = account_data.name
    if account_data.currency is not None:
        account.currency = account_data.currency
    if account_data.account_number is not None:
        account.account_number = account_data.account_number

    db.commit()
    db.refresh(account, ["bank"])
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete account and all related data."""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id,
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    db.delete(account)
    db.commit()
