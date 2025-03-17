"""Fix database state

Revision ID: <unique_id>
Revises: None
Create Date: 2025-03-16 13:10:04.960041

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<unique_id>'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавьте здесь команды для фиксации текущего состояния базы данных
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Добавьте здесь команды для отката изменений
    pass