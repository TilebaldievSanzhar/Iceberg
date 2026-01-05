from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal["income", "expense"]


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[Literal["income", "expense"]] = None


class CategoryResponse(CategoryBase):
    id: UUID
    user_id: Optional[UUID]
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True
