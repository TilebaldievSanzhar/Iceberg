from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class BankResponse(BaseModel):
    id: UUID
    name: str
    country: str
    parser_type: str
    created_at: datetime

    class Config:
        from_attributes = True
