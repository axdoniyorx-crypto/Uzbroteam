from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from services.logger import logger as logging
from services.storage.db import DataBase

logging = logging.bind(service="subscription")

_MEMBER_OK_STATUSES = {"member", "administrator", "creator"}


class SubscriptionManager:
    def __init__(self, db: DataBase, bot: Bot | None = None):
        self.db = db
        self.bot = bot

    # ------------------------------------------------------------------
    # Feature toggles
    # ------------------------------------------------------------------
    async def is_mandatory_subscription_feature_enabled(self) -> bool:
        """Global admin toggle: whether the mandatory subscription gate
        should be enforced at all, independent of which channels exist."""
        return await self.db.is_mandatory_subscription_enabled()

    async def set_mandatory_subscription_feature_enabled(self, enabled: bool) -> None:
        await self.db.set_mandatory_subscription_enabled(enabled)

    async def is_optional_channel_feature_enabled(self) -> bool:
        return await self.db.is_optional_channel_enabled()

    async def set_optional_channel_feature_enabled(self, enabled: bool) -> None:
        await self.db.set_optional_channel_enabled(enabled)

    # ------------------------------------------------------------------
    # Channel management (admin side)
    # ------------------------------------------------------------------
    async def add_channel(
        self,
        channel_id: int,
        title: str,
        url: str,
        subscription_type: str = "mandatory",
        username: str | None = None,
    ) -> None:
        await self.db.add_channel(
            channel_id=channel_id,
            title=title,
            url=url,
            subscription_type=subscription_type,
            username=username,
        )

    async def get_channels(
        self, subscription_type: str | None = None, only_active: bool = True
    ) -> list[dict]:
        return await self.db.get_all_channels(
            subscription_type=subscription_type, only_active=only_active
        )

    async def get_channel(self, channel_id: int) -> dict | None:
        return await self.db.get_channel(channel_id)

    async def update_channel(self, channel_id: int, **fields) -> bool:
        return await self.db.update_channel(channel_id, **fields)

    async def set_channel_active(self, channel_id: int, is_active: bool) -> bool:
        return await self.db.set_channel_active(channel_id, is_active)

    async def delete_channel(self, channel_id: int) -> bool:
        return await self.db.delete_channel(channel_id)

    # ------------------------------------------------------------------
    # Real-time membership verification against Telegram
    # ------------------------------------------------------------------
    async def _is_user_member_of(self, user_id: int, channel_id: int) -> bool:
        """Ask Telegram directly whether the user is currently a member of
        the given channel. This is the source of truth; local DB flags are
        only used as a best-effort cache for analytics/UI, never to gate
        access."""
        if self.bot is None:
            logging.warning(
                "SubscriptionManager has no bot instance; cannot verify "
                "membership for channel %s, assuming not subscribed",
                channel_id,
            )
            return False
        try:
            member = await self.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            is_member = member.status in _MEMBER_OK_STATUSES
            return is_member
        except TelegramForbiddenError:
            logging.warning(
                "Bot lacks access to channel %s (not admin?); treating "
                "membership check as failed", channel_id
            )
            return False
        except TelegramBadRequest as exc:
            logging.warning(
                "Bad request checking membership for user=%s channel=%s: %s",
                user_id, channel_id, exc,
            )
            return False
        except TelegramAPIError as exc:
            logging.error(
                "Telegram API error checking membership for user=%s channel=%s: %s",
                user_id, channel_id, exc,
            )
            return False

    async def check_user_has_mandatory_subscriptions(self, user_id: int) -> bool:
        """Check if user is subscribed to every mandatory channel, verified
        live against the Telegram API (not a cached DB flag)."""
        if not await self.is_mandatory_subscription_feature_enabled():
            return True

        mandatory_channels = await self.get_channels(subscription_type="mandatory")
        if not mandatory_channels:
            return True

        for channel in mandatory_channels:
            is_member = await self._is_user_member_of(user_id, channel["channel_id"])
            await self.db.set_user_subscription(
                user_id, channel["channel_id"], is_member
            )
            if not is_member:
                return False
        return True

    async def get_subscription_status(self, user_id: int) -> dict:
        """Get user subscription status with channel details, verified live
        against Telegram for mandatory channels."""
        mandatory_channels = await self.get_channels(subscription_type="mandatory")
        optional_channels = (
            await self.get_channels(subscription_type="optional")
            if await self.is_optional_channel_feature_enabled()
            else []
        )

        mandatory_subscribed = []
        mandatory_not_subscribed = []
        for channel in mandatory_channels:
            is_member = await self._is_user_member_of(user_id, channel["channel_id"])
            await self.db.set_user_subscription(
                user_id, channel["channel_id"], is_member
            )
            if is_member:
                mandatory_subscribed.append(channel)
            else:
                mandatory_not_subscribed.append(channel)

        return {
            "mandatory": {
                "channels": mandatory_channels,
                "subscribed": mandatory_subscribed,
                "not_subscribed": mandatory_not_subscribed,
            },
            "optional": {
                "channels": optional_channels,
                "subscribed": [],
                "not_subscribed": optional_channels,
            },
        }

    async def get_unsubscribed_channels(self, user_id: int) -> list[dict]:
        """Get list of mandatory channels the user is not currently
        subscribed to (verified live)."""
        status = await self.get_subscription_status(user_id)
        return status["mandatory"]["not_subscribed"]
