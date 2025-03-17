"""Rename requests to orders and update schema

Revision ID: d4ba29d94319
Revises: fb5ae4b442eb
Create Date: 2025-03-16 13:10:04.960041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4ba29d94319'
down_revision: Union[str, None] = 'fb5ae4b442eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Проверка существования таблицы перед переименованием
    if op.get_bind().dialect.has_table(op.get_bind(), 'requests'):
        op.rename_table('requests', 'orders')
    else:
        print("Таблица 'requests' не существует, переименование невозможно.")
        return

    op.add_column('orders', sa.Column('loading_city', sa.String(), nullable=False))
    op.add_column('orders', sa.Column('unloading_city', sa.String(), nullable=False))
    op.add_column('orders', sa.Column('logistician_name', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('order_type', sa.String(), nullable=True))  # Добавляем столбец без ограничения NOT NULL

    # Обновляем существующие строки, устанавливая значение по умолчанию для order_type
    op.execute("UPDATE orders SET order_type = 'UNKNOWN' WHERE order_type IS NULL")

    # Добавляем ограничение NOT NULL
    op.alter_column('orders', 'order_type', nullable=False)

    op.drop_column('orders', 'loading_city_id')
    op.drop_column('orders', 'unloading_city_id')
    op.drop_column('orders', 'logistician_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table('orders', 'requests')
    op.add_column('requests', sa.Column('loading_city_id', sa.Integer(), nullable=False))
    op.add_column('requests', sa.Column('unloading_city_id', sa.Integer(), nullable=False))
    op.add_column('requests', sa.Column('logistician_id', sa.Integer(), nullable=False))
    op.drop_column('requests', 'loading_city')
    op.drop_column('requests', 'unloading_city')
    op.drop_column('requests', 'logistician_name')
    op.drop_column('requests', 'order_type')
