"""Seed initial data

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed banks
    banks_table = sa.table(
        'banks',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('name', sa.String),
        sa.column('country', sa.String),
        sa.column('parser_type', sa.String),
    )

    op.bulk_insert(banks_table, [
        {
            'id': uuid.uuid4(),
            'name': 'Mbank',
            'country': 'KG',
            'parser_type': 'mbank_pdf',
        },
        {
            'id': uuid.uuid4(),
            'name': 'Bakai Bank',
            'country': 'KG',
            'parser_type': 'bakai_pdf',
        },
        {
            'id': uuid.uuid4(),
            'name': 'O!Bank',
            'country': 'KG',
            'parser_type': 'obank_pdf',
        },
        {
            'id': uuid.uuid4(),
            'name': 'Optima Bank',
            'country': 'KG',
            'parser_type': 'optima_pdf',
        },
    ])

    # Seed system categories
    categories_table = sa.table(
        'categories',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('user_id', postgresql.UUID(as_uuid=True)),
        sa.column('name', sa.String),
        sa.column('type', sa.String),
        sa.column('is_system', sa.Boolean),
    )

    # Expense categories
    expense_categories = [
        'Еда и продукты',
        'Транспорт',
        'Развлечения',
        'Покупки',
        'Здоровье',
        'Коммунальные услуги',
        'Связь и интернет',
        'Образование',
        'Путешествия',
        'Рестораны и кафе',
        'Одежда и обувь',
        'Красота и уход',
        'Подарки',
        'Прочие расходы',
    ]

    # Income categories
    income_categories = [
        'Зарплата',
        'Подработка',
        'Проценты по вкладам',
        'Возврат долга',
        'Подарки',
        'Прочие доходы',
    ]

    # Transfer category
    transfer_categories = [
        'Переводы',
    ]

    categories_data = []

    for name in expense_categories:
        categories_data.append({
            'id': uuid.uuid4(),
            'user_id': None,
            'name': name,
            'type': 'expense',
            'is_system': True,
        })

    for name in income_categories:
        categories_data.append({
            'id': uuid.uuid4(),
            'user_id': None,
            'name': name,
            'type': 'income',
            'is_system': True,
        })

    op.bulk_insert(categories_table, categories_data)


def downgrade() -> None:
    # Delete seeded data
    op.execute("DELETE FROM categories WHERE is_system = true")
    op.execute("DELETE FROM banks")
