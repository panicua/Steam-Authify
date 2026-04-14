"""unique steam account per user

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    dup_names = bind.execute(sa.text(
        "SELECT user_id, account_name, COUNT(*) AS c "
        "FROM steam_accounts "
        "GROUP BY user_id, account_name HAVING COUNT(*) > 1"
    )).fetchall()
    dup_steamids = bind.execute(sa.text(
        "SELECT user_id, steam_id, COUNT(*) AS c "
        "FROM steam_accounts "
        "WHERE steam_id IS NOT NULL "
        "GROUP BY user_id, steam_id HAVING COUNT(*) > 1"
    )).fetchall()
    if dup_names or dup_steamids:
        details = []
        for r in dup_names:
            details.append(f"user_id={r.user_id} account_name={r.account_name!r} count={r.c}")
        for r in dup_steamids:
            details.append(f"user_id={r.user_id} steam_id={r.steam_id} count={r.c}")
        raise RuntimeError(
            "Cannot apply 0004 migration: duplicate steam_accounts rows exist. "
            "Remove duplicates manually and rerun. Offenders:\n  "
            + "\n  ".join(details)
        )

    op.create_unique_constraint(
        "uq_steam_accounts_user_account_name",
        "steam_accounts",
        ["user_id", "account_name"],
    )
    op.create_index(
        "uq_steam_accounts_user_steam_id",
        "steam_accounts",
        ["user_id", "steam_id"],
        unique=True,
        postgresql_where=sa.text("steam_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_steam_accounts_user_steam_id", table_name="steam_accounts")
    op.drop_constraint("uq_steam_accounts_user_account_name", "steam_accounts", type_="unique")
