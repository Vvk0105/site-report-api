"""subscription uses plan

Revision ID: 2f78786ac383
Revises: 8a380539eb49
Create Date: 2026-07-15 20:07:19.428093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2f78786ac383'
down_revision: Union[str, Sequence[str], None] = '8a380539eb49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    # 1. Add the new nullable column first
    op.add_column(
        "subscriptions",
        sa.Column(
            "plan_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # 2. Create foreign key
    op.create_foreign_key(
        "fk_subscription_plan",
        "subscriptions",
        "plans",
        ["plan_id"],
        ["id"],
    )

    # 3. Set all existing subscriptions to Trial plan
    op.execute("""
    INSERT INTO plans (
        name,
        description,
        price,
        currency,
        billing_cycle,
        report_limit,
        trial_days,
        is_trial,
        is_active,
        created_at,
        updated_at
    )
    SELECT
        'Trial',
        'Free Trial',
        0,
        'USD',
        'year',
        5,
        30,
        TRUE,
        TRUE,
        NOW(),
        NOW()
    WHERE NOT EXISTS (
        SELECT 1
        FROM plans
        WHERE is_trial = TRUE
    );
    """)

    op.execute("""
    UPDATE subscriptions
    SET plan_id = (
        SELECT id
        FROM plans
        WHERE is_trial = TRUE
        LIMIT 1
    );
    """)

    # 4. Make plan_id mandatory
    op.alter_column(
        "subscriptions",
        "plan_id",
        nullable=False,
    )

    # 5. Remove old columns
    op.drop_column(
        "subscriptions",
        "report_limit",
    )

    op.drop_column(
        "subscriptions",
        "plan_type",
    )


def downgrade():
    pass
