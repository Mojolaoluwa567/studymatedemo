"""add copy_attempt_count to attempt

Revision ID: 7f2b1c9e4a3d
Revises: 3d87fe9e49cb
Create Date: 2026-07-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f2b1c9e4a3d'
down_revision = '3d87fe9e49cb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('attempt', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('copy_attempt_count', sa.Integer(), nullable=True, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('attempt', schema=None) as batch_op:
        batch_op.drop_column('copy_attempt_count')
