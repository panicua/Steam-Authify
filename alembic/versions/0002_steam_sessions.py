"""add steam session columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('steam_accounts', sa.Column('steam_session_encrypted', sa.LargeBinary(), nullable=True))
    op.add_column('steam_accounts', sa.Column('session_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('steam_accounts', 'session_expires_at')
    op.drop_column('steam_accounts', 'steam_session_encrypted')
