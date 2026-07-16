"""payment table status update with enum

Revision ID: 40aad17952e1
Revises: 54b1f306f33f
Create Date: 2026-07-16 16:26:59.029592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40aad17952e1'
down_revision: Union[str, Sequence[str], None] = '54b1f306f33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the Enum type in PostgreSQL
    payment_status_enum = sa.Enum('PAID', 'FAILED', 'PENDING', 'REFUNDED', name='paymentstatus')
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    # Cast existing status string values to uppercase to match Python enum names
    op.execute("UPDATE payments SET status = UPPER(status)")

    # Alter status column to type enum
    op.alter_column('payments', 'status',
               existing_type=sa.VARCHAR(length=30),
               type_=payment_status_enum,
               existing_nullable=False,
               postgresql_using='status::paymentstatus')


def downgrade() -> None:
    """Downgrade schema."""
    # Alter status column back to VARCHAR
    op.alter_column('payments', 'status',
               existing_type=sa.Enum('PAID', 'FAILED', 'PENDING', 'REFUNDED', name='paymentstatus'),
               type_=sa.VARCHAR(length=30),
               existing_nullable=False)

    # Convert uppercase values back to lowercase
    op.execute("UPDATE payments SET status = LOWER(status)")

    # Drop the Enum type from PostgreSQL
    payment_status_enum = sa.Enum('PAID', 'FAILED', 'PENDING', 'REFUNDED', name='paymentstatus')
    payment_status_enum.drop(op.get_bind(), checkfirst=True)

