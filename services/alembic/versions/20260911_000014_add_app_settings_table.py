"""add app_settings table for global feature toggles

Revision ID: 20260911_000014
Revises: 20260909_000013
Create Date: 2026-09-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260911_000014'
down_revision = '20260909_000013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'app_settings',
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('key'),
    )
    # Preserve existing behaviour on upgrade: mandatory subscription stays ON
    # unless an admin explicitly turns it off from the admin panel.
    op.execute(
        "INSERT INTO app_settings (key, value) VALUES "
        "('mandatory_subscription_enabled', 'on')"
    )


def downgrade() -> None:
    op.drop_table('app_settings')
