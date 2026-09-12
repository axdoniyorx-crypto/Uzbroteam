"""add subscription and broadcast tables

Revision ID: 20260909_000013
Revises: 20260908_000012
Create Date: 2026-09-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260909_000013'
down_revision = '20260908_000012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create channels table
    op.create_table(
        'channels',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('channel_id', sa.BigInteger(), nullable=False, unique=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('subscription_type', sa.Text(), nullable=False, server_default='mandatory'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_channels_channel_id', 'channels', ['channel_id'])
    op.create_index('ix_channels_is_active', 'channels', ['is_active'])

    # Create channel_subscriptions table
    op.create_table(
        'channel_subscriptions',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('is_subscribed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('subscribed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('checked_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'channel_id', name='uq_user_channel'),
    )
    op.create_index('ix_channel_subscriptions_user_id', 'channel_subscriptions', ['user_id'])
    op.create_index('ix_channel_subscriptions_channel_id', 'channel_subscriptions', ['channel_id'])

    # Create broadcast_messages table
    op.create_table(
        'broadcast_messages',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=False),
        sa.Column('target_type', sa.Text(), nullable=False, server_default='all'),
        sa.Column('status', sa.Text(), nullable=False, server_default='draft'),
        sa.Column('sent_count', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column('failed_count', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_broadcast_messages_created_at', 'broadcast_messages', ['created_at'])
    op.create_index('ix_broadcast_messages_status', 'broadcast_messages', ['status'])


def downgrade() -> None:
    op.drop_table('broadcast_messages')
    op.drop_table('channel_subscriptions')
    op.drop_table('channels')
