from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


class SummaryResponse(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    transaction_count: int
    date_from: date
    date_to: date


class CategoryStats(BaseModel):
    category_id: Optional[UUID]
    category_name: str
    total_amount: Decimal
    transaction_count: int
    percentage: float  # Percentage of total


class PeriodStats(BaseModel):
    period: str  # "2024-01", "2024-W01", "2024-01-15" depending on grouping
    income: Decimal
    expense: Decimal
    balance: Decimal
    transaction_count: int


class AccountStats(BaseModel):
    account_id: UUID
    account_name: str
    currency: str
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    transaction_count: int


class AnalyticsByCategoryResponse(BaseModel):
    date_from: date
    date_to: date
    type: str  # "income" or "expense"
    total: Decimal
    categories: List[CategoryStats]


class AnalyticsByPeriodResponse(BaseModel):
    date_from: date
    date_to: date
    grouping: str  # "day", "week", "month"
    periods: List[PeriodStats]


class AnalyticsByAccountResponse(BaseModel):
    date_from: date
    date_to: date
    accounts: List[AccountStats]
