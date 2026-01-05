from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.category import CategoryResponse


class RuleBase(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=255)
    match_type: Literal["exact", "contains", "regex"]
    priority: int = Field(default=0, ge=0)


class RuleCreate(RuleBase):
    category_id: UUID


class RuleResponse(RuleBase):
    id: UUID
    user_id: Optional[UUID]
    category_id: UUID
    created_at: datetime
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True
