"""Create Platform

Revision ID: 72f382114c8f
Revises: 7959894cb5f5
Create Date: 2025-03-20 10:59:13.032781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '72f382114c8f'
down_revision: Union[str, None] = '7959894cb5f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: добавление таблицы Platform и обновление distribution_rules"""
    
    # 1️⃣ Создаём таблицу `platforms`
    op.create_table(
        'platforms',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default="true", nullable=False),
        sa.Column('auth_data', postgresql.JSON(), nullable=True)
    )

    # 2️⃣ Добавляем колонку `platform` в `distribution_rules`
    op.add_column('distribution_rules', sa.Column('platform', sa.String(), nullable=True))

    # 3️⃣ Заполняем `platform` значением по умолчанию
    op.execute("UPDATE distribution_rules SET platform = 'Transport2'")

    # 4️⃣ Делаем колонку `platform` NOT NULL
    op.alter_column('distribution_rules', 'platform', nullable=False)

    # 5️⃣ Добавляем индекс для ускорения поиска
    op.create_index('ix_distribution_rules_platform', 'distribution_rules', ['platform'], unique=False)


def downgrade() -> None:
    """Downgrade schema: удаление платформы"""
    
    # 1️⃣ Удаляем индекс
    op.drop_index('ix_distribution_rules_platform', table_name='distribution_rules')

    # 2️⃣ Удаляем колонку `platform` из `distribution_rules`
    op.drop_column('distribution_rules', 'platform')

    # 3️⃣ Удаляем таблицу `platforms`
    op.drop_table('platforms')
    # ### end Alembic commands ###
