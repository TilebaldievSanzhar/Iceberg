"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Banks table
    op.create_table(
        'banks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('country', sa.String(2), nullable=False),
        sa.Column('parser_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(10), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Accounts table
    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bank_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('banks.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('account_number', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Uploads table
    op.create_table(
        'uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('upload_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('uploads.id', ondelete='SET NULL'), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('type', sa.String(10), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('counterparty', sa.String(255), nullable=True),
        sa.Column('original_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('original_description', sa.Text(), nullable=True),
        sa.Column('original_counterparty', sa.String(255), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for transactions
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'date'])
    op.create_index('ix_transactions_category', 'transactions', ['category_id'])
    op.create_index('ix_transactions_upload', 'transactions', ['upload_id'])

    # Categorization rules table
    op.create_table(
        'categorization_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pattern', sa.String(255), nullable=False),
        sa.Column('match_type', sa.String(20), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('categorization_rules')
    op.drop_index('ix_transactions_upload', table_name='transactions')
    op.drop_index('ix_transactions_category', table_name='transactions')
    op.drop_index('ix_transactions_account_date', table_name='transactions')
    op.drop_table('transactions')
    op.drop_table('uploads')
    op.drop_table('accounts')
    op.drop_table('categories')
    op.drop_table('banks')
    op.drop_table('users')
