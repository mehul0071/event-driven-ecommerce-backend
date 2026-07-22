"""add timestamps to products

Revision ID: b03bdba229de
Revises: 5caccfa1a0b7
Create Date: 2026-07-22 15:18:11.990587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b03bdba229de'
down_revision: Union[str, None] = '5caccfa1a0b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('products', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'created_at')
