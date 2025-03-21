"""Initial migration

Revision ID: 6d2a38d4873d
Revises: 
Create Date: 2025-03-13 14:41:37.960988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6d2a38d4873d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('logists',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('contact_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='logists_pkey'),
    sa.UniqueConstraint('name', name='logists_name_key')
    )
    op.create_table('users',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('users_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('username', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('password_hash', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='users_pkey'),
    sa.UniqueConstraint('email', name='users_email_key'),
    sa.UniqueConstraint('username', name='users_username_key'),
    postgresql_ignore_search_path=False
    )
    op.create_table('distribution_rules',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('loading_city_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('unloading_city_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('logist_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('margin_percent', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('auction_margin_percent', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('cargo_name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('auto_publish', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('publish_delay', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='distribution_rules_pkey')
    )
    op.create_table('requests',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('external_no', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('loading_city_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('unloading_city_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('load_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('unload_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('weight', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('volume', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('logistician', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('ati_price', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('is_published', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('is_auction', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('platform', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name='requests_owner_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='requests_pkey'),
    sa.UniqueConstraint('external_no', name='requests_external_no_key')
    )
    # ### end Alembic commands ###
