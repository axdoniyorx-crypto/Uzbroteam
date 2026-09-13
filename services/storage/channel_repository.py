from sqlalchemy import delete, select, update
from services.logger import logger as logging
from services.storage.models import Channel, ChannelSubscription

logging = logging.bind(service="db_channels")


class ChannelRepositoryMixin:
    async def add_channel(
        self,
        channel_id: int,
        title: str,
        url: str,
        subscription_type: str = "mandatory",
        username: str | None = None,
    ) -> None:
        async with self.SessionLocal() as session:
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            existing = await session.execute(stmt)
            if existing.scalar():
                logging.debug(f"Channel {channel_id} already exists")
                return

            channel = Channel(
                channel_id=channel_id,
                title=title,
                url=url,
                username=username,
                subscription_type=subscription_type,
            )
            session.add(channel)
            await session.commit()
            logging.event("channel_added", channel_id=channel_id, type=subscription_type)

    async def get_channel(self, channel_id: int) -> dict | None:
        async with self.SessionLocal() as session:
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            result = await session.execute(stmt)
            ch = result.scalar()
            if not ch:
                return None
            return {
                "channel_id": ch.channel_id,
                "title": ch.title,
                "url": ch.url,
                "username": ch.username,
                "type": ch.subscription_type,
                "is_active": ch.is_active,
            }

    async def get_all_channels(
        self, subscription_type: str | None = None, only_active: bool = True
    ) -> list[dict]:
        async with self.SessionLocal() as session:
            query = select(Channel)
            if only_active:
                query = query.where(Channel.is_active == True)
            if subscription_type:
                query = query.where(Channel.subscription_type == subscription_type)
            result = await session.execute(query)
            channels = result.scalars().all()
            return [
                {
                    "channel_id": ch.channel_id,
                    "title": ch.title,
                    "url": ch.url,
                    "username": ch.username,
                    "type": ch.subscription_type,
                    "is_active": ch.is_active,
                }
                for ch in channels
            ]

    async def update_channel(
        self,
        channel_id: int,
        *,
        title: str | None = None,
        url: str | None = None,
        username: str | None = None,
    ) -> bool:
        values: dict = {}
        if title is not None:
            values["title"] = title
        if url is not None:
            values["url"] = url
        if username is not None:
            values["username"] = username
        if not values:
            return False
        async with self.SessionLocal() as session:
            result = await session.execute(
                update(Channel).where(Channel.channel_id == channel_id).values(**values)
            )
            await session.commit()
            updated = result.rowcount > 0
            if updated:
                logging.event("channel_updated", channel_id=channel_id, **values)
            return updated

    async def set_channel_active(self, channel_id: int, is_active: bool) -> bool:
        async with self.SessionLocal() as session:
            result = await session.execute(
                update(Channel)
                .where(Channel.channel_id == channel_id)
                .values(is_active=is_active)
            )
            await session.commit()
            updated = result.rowcount > 0
            if updated:
                logging.event(
                    "channel_active_toggled", channel_id=channel_id, is_active=is_active
                )
            return updated

    async def delete_channel(self, channel_id: int) -> bool:
        async with self.SessionLocal() as session:
            await session.execute(
                delete(ChannelSubscription).where(
                    ChannelSubscription.channel_id == channel_id
                )
            )
            result = await session.execute(
                delete(Channel).where(Channel.channel_id == channel_id)
            )
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logging.event("channel_deleted", channel_id=channel_id)
            return deleted

    async def set_user_subscription(
        self, user_id: int, channel_id: int, is_subscribed: bool
    ) -> None:
        async with self.SessionLocal() as session:
            stmt = select(ChannelSubscription).where(
                (ChannelSubscription.user_id == user_id)
                & (ChannelSubscription.channel_id == channel_id)
            )
            existing = await session.execute(stmt)
            sub = existing.scalar()

            if sub:
                sub.is_subscribed = is_subscribed
                if is_subscribed:
                    from datetime import datetime
                    sub.subscribed_at = datetime.utcnow()
            else:
                from datetime import datetime
                sub = ChannelSubscription(
                    user_id=user_id,
                    channel_id=channel_id,
                    is_subscribed=is_subscribed,
                    subscribed_at=datetime.utcnow() if is_subscribed else None,
                )
                session.add(sub)

            await session.commit()
            logging.debug(f"User {user_id} subscription to {channel_id}: {is_subscribed}")

    async def get_user_subscriptions(self, user_id: int) -> dict:
        async with self.SessionLocal() as session:
            stmt = select(ChannelSubscription).where(ChannelSubscription.user_id == user_id)
            result = await session.execute(stmt)
            subs = result.scalars().all()

            return {
                "mandatory": [s.channel_id for s in subs if s.is_subscribed],
                "not_subscribed": [s.channel_id for s in subs if not s.is_subscribed],
            }

    async def check_mandatory_subscriptions(self, user_id: int) -> bool:
        """Deprecated cached-flag check, kept for backward compatibility.

        Real-time verification against the Telegram API now happens in
        SubscriptionManager.check_user_has_mandatory_subscriptions, which
        calls bot.get_chat_member for each mandatory channel directly
        instead of relying on this locally cached table.
        """
        async with self.SessionLocal() as session:
            stmt = select(ChannelSubscription).where(
                (ChannelSubscription.user_id == user_id)
                & (ChannelSubscription.is_subscribed == False)
            )
            result = await session.execute(stmt)
            unsubscribed = result.scalars().all()

            if not unsubscribed:
                return True

            stmt = select(Channel).where(
                (Channel.channel_id.in_([s.channel_id for s in unsubscribed]))
                & (Channel.subscription_type == "mandatory")
            )
            result = await session.execute(stmt)
            mandatory = result.scalars().all()

            return len(mandatory) == 0
