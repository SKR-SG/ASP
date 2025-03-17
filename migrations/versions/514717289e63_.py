"""empty message

Revision ID: 514717289e63
Revises: d4ba29d94319, <unique_id>
Create Date: 2025-03-16 15:10:18.248194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '514717289e63'
down_revision: Union[str, None] = ('d4ba29d94319', '<unique_id>')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
