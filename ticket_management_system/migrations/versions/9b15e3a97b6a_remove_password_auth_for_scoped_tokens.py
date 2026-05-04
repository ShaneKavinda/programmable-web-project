"""Remove password auth for scoped user-id tokens

Revision ID: 9b15e3a97b6a
Revises: 4184671b7fac
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b15e3a97b6a'
down_revision = '4184671b7fac'
branch_labels = None
depends_on = None


def upgrade():
    """Drop password hashes; auth tokens are issued from user identity."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('password_hash')


def downgrade():
    """Restore password_hash for rollback compatibility."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'password_hash',
                sa.String(length=255),
                nullable=False,
                server_default='',
            )
        )
        batch_op.alter_column('password_hash', server_default=None)
