from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_id: UUID
    filename: str
    file_path: str
    status: Literal["pending", "processing", "done", "error"]
    error_message: Optional[str]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    transaction_count: Optional[int] = None

    class Config:
        from_attributes = True
