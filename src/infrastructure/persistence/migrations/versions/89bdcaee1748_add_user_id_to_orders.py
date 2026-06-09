"""add user_id to orders table
Revision ID: 89bdcaee1748
Revises: c148dc8f20b7
Create Date: 2026-05-09 19:45:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '89bdcaee1748'
down_revision = 'c148dc8f20b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', 
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    op.create_index(op.f('ix_orders_user_id'), 'orders', ['user_id'], unique=False)
    
    op.create_foreign_key(
        'fk_orders_user_id',
        'orders', 
        'users', 
        ['user_id'], 
        ['id'],
        ondelete='CASCADE'
    )

    op.execute("""
        UPDATE orders 
        SET user_id = '2e1b4a45-6ff6-408d-a4c9-3c9b4620b647' 
        WHERE user_id IS NULL
    """)

    op.alter_column('orders', 'user_id', nullable=False)


def downgrade() -> None:
    op.drop_constraint('fk_orders_user_id', 'orders', type_='foreignkey')
    op.drop_index(op.f('ix_orders_user_id'), table_name='orders')
    op.drop_column('orders', 'user_id')