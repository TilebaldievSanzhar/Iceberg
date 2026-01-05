from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models import Transaction, Category, Account
from app.schemas.analytics import (
    SummaryResponse,
    CategoryStats,
    PeriodStats,
    AccountStats,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        account_ids: Optional[List[UUID]] = None,
    ) -> SummaryResponse:
        query = (
            self.db.query(
                func.sum(case((Transaction.type == "income", Transaction.amount), else_=Decimal(0))).label("income"),
                func.sum(case((Transaction.type == "expense", Transaction.amount), else_=Decimal(0))).label("expense"),
                func.count(Transaction.id).label("count"),
            )
            .join(Account)
            .filter(
                Account.user_id == user_id,
                Transaction.date >= date_from,
                Transaction.date <= date_to,
            )
        )

        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))

        result = query.first()

        total_income = result.income or Decimal(0)
        total_expense = result.expense or Decimal(0)

        return SummaryResponse(
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
            transaction_count=result.count or 0,
            date_from=date_from,
            date_to=date_to,
        )

    def get_by_category(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        transaction_type: Literal["income", "expense"] = "expense",
        account_ids: Optional[List[UUID]] = None,
    ) -> List[CategoryStats]:
        query = (
            self.db.query(
                Category.id,
                Category.name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .outerjoin(Transaction, Transaction.category_id == Category.id)
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Account.user_id == user_id,
                Transaction.date >= date_from,
                Transaction.date <= date_to,
                Transaction.type == transaction_type,
            )
            .group_by(Category.id, Category.name)
        )

        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))

        results = query.all()

        # Calculate total for percentages
        total = sum(r.total or Decimal(0) for r in results)

        stats = []
        for r in results:
            amount = r.total or Decimal(0)
            stats.append(CategoryStats(
                category_id=r.id,
                category_name=r.name or "Uncategorized",
                total_amount=amount,
                transaction_count=r.count or 0,
                percentage=float(amount / total * 100) if total > 0 else 0,
            ))

        # Sort by amount descending
        stats.sort(key=lambda x: x.total_amount, reverse=True)
        return stats

    def get_by_period(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        grouping: Literal["day", "week", "month"] = "month",
        account_ids: Optional[List[UUID]] = None,
    ) -> List[PeriodStats]:
        # Build date truncation expression based on grouping
        if grouping == "day":
            date_expr = func.date_trunc("day", Transaction.date)
            format_str = "%Y-%m-%d"
        elif grouping == "week":
            date_expr = func.date_trunc("week", Transaction.date)
            format_str = "%Y-W%W"
        else:  # month
            date_expr = func.date_trunc("month", Transaction.date)
            format_str = "%Y-%m"

        query = (
            self.db.query(
                date_expr.label("period"),
                func.sum(case((Transaction.type == "income", Transaction.amount), else_=Decimal(0))).label("income"),
                func.sum(case((Transaction.type == "expense", Transaction.amount), else_=Decimal(0))).label("expense"),
                func.count(Transaction.id).label("count"),
            )
            .join(Account)
            .filter(
                Account.user_id == user_id,
                Transaction.date >= date_from,
                Transaction.date <= date_to,
            )
            .group_by(date_expr)
            .order_by(date_expr)
        )

        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))

        results = query.all()

        stats = []
        for r in results:
            income = r.income or Decimal(0)
            expense = r.expense or Decimal(0)
            stats.append(PeriodStats(
                period=r.period.strftime(format_str) if r.period else "",
                income=income,
                expense=expense,
                balance=income - expense,
                transaction_count=r.count or 0,
            ))

        return stats

    def get_by_account(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> List[AccountStats]:
        results = (
            self.db.query(
                Account.id,
                Account.name,
                Account.currency,
                func.sum(case((Transaction.type == "income", Transaction.amount), else_=Decimal(0))).label("income"),
                func.sum(case((Transaction.type == "expense", Transaction.amount), else_=Decimal(0))).label("expense"),
                func.count(Transaction.id).label("count"),
            )
            .outerjoin(
                Transaction,
                (Transaction.account_id == Account.id) &
                (Transaction.date >= date_from) &
                (Transaction.date <= date_to)
            )
            .filter(Account.user_id == user_id)
            .group_by(Account.id, Account.name, Account.currency)
            .all()
        )

        stats = []
        for r in results:
            income = r.income or Decimal(0)
            expense = r.expense or Decimal(0)
            stats.append(AccountStats(
                account_id=r.id,
                account_name=r.name,
                currency=r.currency,
                total_income=income,
                total_expense=expense,
                balance=income - expense,
                transaction_count=r.count or 0,
            ))

        return stats
