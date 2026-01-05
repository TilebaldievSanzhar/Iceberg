from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Literal, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.category import CategoryResponse


class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    type: Literal["income", "expense", "transfer"]
    date: date
    description: Optional[str] = None
    counterparty: Optional[str] = Field(None, max_length=255)


class TransactionCreate(TransactionBase):
    account_id: UUID
    category_id: Optional[UUID] = None


class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    type: Optional[Literal["income", "expense", "transfer"]] = None
    date: Optional[date] = None
    description: Optional[str] = None
    counterparty: Optional[str] = Field(None, max_length=255)
    category_id: Optional[UUID] = None


class TransactionResponse(TransactionBase):
    id: UUID
    account_id: UUID
    upload_id: Optional[UUID]
    category_id: Optional[UUID]
    original_amount: Optional[Decimal]
    original_description: Optional[str]
    original_counterparty: Optional[str]
    is_edited: bool
    created_at: datetime
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    account_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    types: Optional[List[Literal["income", "expense", "transfer"]]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    search: Optional[str] = None  # Search in description/counterparty