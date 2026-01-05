from typing import Generic, TypeVar, List, Optional
from uuid import UUID
from pydantic import BaseModel

T = TypeVar("T")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: UUID
    exp: int
    type: str  # "access" or "refresh"


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
