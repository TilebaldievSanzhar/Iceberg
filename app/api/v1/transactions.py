from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user
from app.models import User, Transaction, Account, Category
from app.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
)

router = APIRouter()


@router.get("", response_model=List[TransactionResponse])
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
):
    """Get transactions with filters."""
    query = (
        db.query(Transaction)
        .join(Account)
        .options(joinedload(Transaction.category))
        .filter(Account.user_id == current_user.id)
    )

    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if min_amount:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount:
        query = query.filter(Transaction.amount <= max_amount)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Transaction.description.ilike(search_filter)) |
            (Transaction.counterparty.ilike(search_filter))
        )

    # Pagination
    offset = (page - 1) * size
    transactions = (
        query
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    return transactions


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    tx_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a manual transaction."""
    # Verify account belongs to user
    account = db.query(Account).filter(
        Account.id == tx_data.account_id,
        Account.user_id == current_user.id,
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Verify category if provided
    if tx_data.category_id:
        category = db.query(Category).filter(
            Category.id == tx_data.category_id,
            (Category.user_id == current_user.id) | (Category.is_system == True)
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

    transaction = Transaction(
        account_id=tx_data.account_id,
        category_id=tx_data.category_id,
        amount=tx_data.amount,
        type=tx_data.type,
        date=tx_data.date,
        description=tx_data.description,
        counterparty=tx_data.counterparty,
        is_edited=False,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction, ["category"])
    return transaction


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get transaction by ID."""
    transaction = (
        db.query(Transaction)
        .join(Account)
        .options(joinedload(Transaction.category))
        .filter(
            Transaction.id == transaction_id,
            Account.user_id == current_user.id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    tx_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update transaction."""
    transaction = (
        db.query(Transaction)
        .join(Account)
        .filter(
            Transaction.id == transaction_id,
            Account.user_id == current_user.id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Store originals if this is first edit
    if not transaction.is_edited and transaction.upload_id:
        if transaction.original_amount is None:
            transaction.original_amount = transaction.amount
        if transaction.original_description is None:
            transaction.original_description = transaction.description
        if transaction.original_counterparty is None:
            transaction.original_counterparty = transaction.counterparty

    # Apply updates
    if tx_data.amount is not None:
        transaction.amount = tx_data.amount
    if tx_data.type is not None:
        transaction.type = tx_data.type
    if tx_data.date is not None:
        transaction.date = tx_data.date
    if tx_data.description is not None:
        transaction.description = tx_data.description
    if tx_data.counterparty is not None:
        transaction.counterparty = tx_data.counterparty
    if tx_data.category_id is not None:
        # Verify category
        category = db.query(Category).filter(
            Category.id == tx_data.category_id,
            (Category.user_id == current_user.id) | (Category.is_system == True)
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        transaction.category_id = tx_data.category_id

    transaction.is_edited = True
    db.commit()
    db.refresh(transaction, ["category"])
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete transaction."""
    transaction = (
        db.query(Transaction)
        .join(Account)
        .filter(
            Transaction.id == transaction_id,
            Account.user_id == current_user.id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    db.delete(transaction)
    db.commit()
