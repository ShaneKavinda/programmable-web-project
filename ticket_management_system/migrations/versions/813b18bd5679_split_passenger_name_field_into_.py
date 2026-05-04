"""Split passenger_name field into passenger_fname and passenger_lname

Revision ID: 813b18bd5679
Revises: 9b15e3a97b6a
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '813b18bd5679'
down_revision = '9b15e3a97b6a'
branch_labels = None
depends_on = None


def upgrade():
    """Split passenger_name into passenger_fname and passenger_lname."""
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('passenger_fname', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('passenger_lname', sa.String(length=50), nullable=True))

    connection = op.get_bind()

    connection.execute(sa.text("""
        UPDATE tickets
        SET
            passenger_fname = CASE
                WHEN passenger_name IS NULL OR btrim(passenger_name) = '' THEN ''
                WHEN position(' ' in btrim(passenger_name)) = 0 THEN btrim(passenger_name)
                ELSE split_part(btrim(passenger_name), ' ', 1)
            END,
            passenger_lname = CASE
                WHEN passenger_name IS NULL OR btrim(passenger_name) = '' THEN ''
                WHEN position(' ' in btrim(passenger_name)) = 0 THEN ''
                ELSE btrim(substr(btrim(passenger_name), position(' ' in btrim(passenger_name)) + 1))
            END
    """))

    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.alter_column('passenger_fname', existing_type=sa.String(length=50), nullable=False)
        batch_op.alter_column('passenger_lname', existing_type=sa.String(length=50), nullable=False)
        batch_op.drop_column('passenger_name')


def downgrade():
    """Merge passenger_fname and passenger_lname back into passenger_name."""
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('passenger_name', sa.String(length=100), nullable=True))

    connection = op.get_bind()

    connection.execute(sa.text("""
        UPDATE tickets
        SET passenger_name = btrim(
            coalesce(passenger_fname, '') ||
            CASE
                WHEN coalesce(passenger_fname, '') != '' AND coalesce(passenger_lname, '') != ''
                THEN ' '
                ELSE ''
            END ||
            coalesce(passenger_lname, '')
        )
    """))

    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.alter_column('passenger_name', existing_type=sa.String(length=100), nullable=False)
        batch_op.drop_column('passenger_fname')
        batch_op.drop_column('passenger_lname')