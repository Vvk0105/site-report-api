"""security and integrity fixes

- reports.client_id (idempotent report start) with a per-user unique constraint
- indexes used by webhooks and admin filters
- refresh tokens are stored as SHA-256 hashes (existing rows are hashed in place,
  so current sessions keep working)

Revision ID: e1a2c3d4f5b6
Revises: 40aad17952e1
Create Date: 2026-10-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a2c3d4f5b6"
down_revision: Union[str, None] = "40aad17952e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The API now looks users up by lowercase email. Older versions stored whatever the user
    # typed, so lowercase the existing rows or those users would be treated as new accounts.
    bind = op.get_bind()
    collisions = bind.execute(
        sa.text(
            "SELECT lower(email), count(*) FROM users "
            "GROUP BY lower(email) HAVING count(*) > 1"
        )
    ).fetchall()
    if collisions:
        names = ", ".join(str(row[0]) for row in collisions)
        raise RuntimeError(
            "Cannot lowercase user emails: these addresses exist more than once with "
            f"different capitalisation: {names}. Merge or remove the duplicates, then re-run."
        )
    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")
    op.execute("UPDATE otp_codes SET email = lower(email) WHERE email <> lower(email)")

    op.add_column("reports", sa.Column("client_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_reports_user_client", "reports", ["user_id", "client_id"])

    op.create_index(op.f("ix_payments_stripe_subscription_id"), "payments", ["stripe_subscription_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_status"), "subscriptions", ["status"], unique=False)
    op.create_index(op.f("ix_login_logs_login_at"), "login_logs", ["login_at"], unique=False)

    # Hash existing plaintext refresh tokens so they are never stored raw again.
    op.execute(
        "UPDATE refresh_tokens "
        "SET token = encode(sha256(convert_to(token, 'UTF8')), 'hex') "
        "WHERE length(token) <> 64"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_login_logs_login_at"), table_name="login_logs")
    op.drop_index(op.f("ix_subscriptions_status"), table_name="subscriptions")
    op.drop_index(op.f("ix_payments_stripe_subscription_id"), table_name="payments")
    op.drop_constraint("uq_reports_user_client", "reports", type_="unique")
    op.drop_column("reports", "client_id")
    # Token hashes cannot be reversed; downgraded installs simply require a fresh sign-in.
