"""add user_id index on steam_accounts

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_steam_accounts_user_id', 'steam_accounts', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_steam_accounts_user_id', table_name='steam_accounts')
