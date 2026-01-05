from datetime import date, timedelta
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.analytics import (
    SummaryResponse,
    AnalyticsByCategoryResponse,
    AnalyticsByPeriodResponse,
    AnalyticsByAccountResponse,
)
from app.services import AnalyticsService

router = APIRouter()


def get_default_date_range() -> tuple[date, date]:
    """Get default date range (current month)."""
    today = date.today()
    date_from = today.replace(day=1)
    # Last day of month
    next_month = date_from.replace(day=28) + timedelta(days=4)
    date_to = next_month - timedelta(days=next_month.day)
    return date_from, date_to


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_ids: Optional[List[UUID]] = Query(None),
):
    """Get financial summary for a period."""
    if not date_from or not date_to:
        date_from, date_to = get_default_date_range()

    service = AnalyticsService(db)
    return service.get_summary(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        account_ids=account_ids,
    )


@router.get("/by-category", response_model=AnalyticsByCategoryResponse)
def get_by_category(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    transaction_type: Literal["income", "expense"] = "expense",
    account_ids: Optional[List[UUID]] = Query(None),
):
    """Get statistics by category."""
    if not date_from or not date_to:
        date_from, date_to = get_default_date_range()

    service = AnalyticsService(db)
    categories = service.get_by_category(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        account_ids=account_ids,
    )

    total = sum(c.total_amount for c in categories)

    return AnalyticsByCategoryResponse(
        date_from=date_from,
        date_to=date_to,
        type=transaction_type,
        total=total,
        categories=categories,
    )


@router.get("/by-period", response_model=AnalyticsByPeriodResponse)
def get_by_period(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    grouping: Literal["day", "week", "month"] = "month",
    account_ids: Optional[List[UUID]] = Query(None),
):
    """Get statistics by time period."""
    if not date_from or not date_to:
        # Default to last 6 months
        today = date.today()
        date_from = (today - timedelta(days=180)).replace(day=1)
        date_to = today

    service = AnalyticsService(db)
    periods = service.get_by_period(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        grouping=grouping,
        account_ids=account_ids,
    )

    return AnalyticsByPeriodResponse(
        date_from=date_from,
        date_to=date_to,
        grouping=grouping,
        periods=periods,
    )


@router.get("/by-account", response_model=AnalyticsByAccountResponse)
def get_by_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Get statistics by account."""
    if not date_from or not date_to:
        date_from, date_to = get_default_date_range()

    service = AnalyticsService(db)
    accounts = service.get_by_account(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
    )

    return AnalyticsByAccountResponse(
        date_from=date_from,
        date_to=date_to,
        accounts=accounts,
    )
