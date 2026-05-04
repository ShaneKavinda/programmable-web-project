"""Drop role column from users table.

Revision ID: c3f1a8d2b7e4
Revises: 813b18bd5679
Create Date: 2026-04-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3f1a8d2b7e4"
down_revision = "813b18bd5679"
branch_labels = None
depends_on = None


def upgrade():
    """Remove users.role as admin now uses API key headers."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS roles")


def downgrade():
    """Restore users.role for rollback compatibility."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.Enum("admin", "user", name="roles"),
                nullable=False,
                server_default="user",
            )
        )
        batch_op.alter_column("role", server_default=None)
