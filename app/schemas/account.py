from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.bank import BankResponse


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    currency: str = Field(..., min_length=3, max_length=3)
    account_number: Optional[str] = Field(None, max_length=50)


class AccountCreate(AccountBase):
    bank_id: UUID


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    account_number: Optional[str] = Field(None, max_length=50)


class AccountResponse(AccountBase):
    id: UUID
    user_id: UUID
    bank_id: UUID
    created_at: datetime
    bank: Optional[BankResponse] = None

    class Config:
        from_attributes = True
