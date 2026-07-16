"""actually add tab_switch_count to attempt

The migration named "add tab_switch_count to attempt" (5a196cdaa0b7)
never actually added the column - its upgrade() only created an
unrelated 'announcement' table, almost certainly from a bad autogenerate
merge. The column has been referenced in models.py and app.py this
whole time without ever existing in the database. This migration
actually adds it.

Revision ID: 9d4e8a1c6b52
Revises: 7f2b1c9e4a3d
Create Date: 2026-07-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d4e8a1c6b52'
down_revision = '7f2b1c9e4a3d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attempt', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('tab_switch_count', sa.Integer(), nullable=True, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('attempt', schema=None) as batch_op:
        batch_op.drop_column('tab_switch_count')
