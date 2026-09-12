"""add scheduled_at to broadcast_messages

Revision ID: 20260912_000015
Revises: 20260911_000014
Create Date: 2026-09-12 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260912_000015'
down_revision = '20260911_000014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'broadcast_messages',
        sa.Column('scheduled_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_broadcast_messages_scheduled_at',
        'broadcast_messages',
        ['scheduled_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_broadcast_messages_scheduled_at', table_name='broadcast_messages')
    op.drop_column('broadcast_messages', 'scheduled_at')
