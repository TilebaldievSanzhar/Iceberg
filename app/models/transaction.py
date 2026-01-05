import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, Text, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_category", "category_id"),
        Index("ix_transactions_upload", "upload_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE")
    )
    upload_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    type: Mapped[str] = mapped_column(String(10))  # income, expense, transfer
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    counterparty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Original values from bank statement (for audit)
    original_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    original_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_counterparty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    account = relationship("Account", back_populates="transactions")
    upload = relationship("Upload", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
