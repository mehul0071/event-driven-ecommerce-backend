"""merge_heads

Revision ID: 96d1c5d1f843
Revises: 1e1699efee13, 89bdcaee1748
Create Date: 2026-07-20 11:35:30.743133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96d1c5d1f843'
down_revision: Union[str, None] = ('1e1699efee13', '89bdcaee1748')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
