from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.logger import logger as logging
from services.subscription import SubscriptionManager
from services.localization import get_text

logging = logging.bind(service="subscription_middleware")

# Commands that must always work, even for users who have not yet joined
# the mandatory channels (otherwise a user could get permanently stuck
# with no way to reach /start or /admin).
_EXCLUDED_COMMANDS = ("/start", "/help", "/settings", "/admin")

CHECK_SUBSCRIPTION_CALLBACK = "check_mandatory_subscription"


def build_subscription_prompt_keyboard(
    channels: list[dict], language: str = "uz"
) -> types.InlineKeyboardMarkup:
    """Build the keyboard shown to a user who hasn't joined all mandatory
    channels: one button per channel plus a final "check again" button."""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        title = channel.get("title") or "Channel"
        url = channel.get("url")
        if url:
            builder.button(text=f"📢 {title}", url=url)
    builder.button(
        text="✅ " + ("Obunani tekshirish" if language == "uz" else "Check subscription"),
        callback_data=CHECK_SUBSCRIPTION_CALLBACK,
    )
    builder.adjust(1)
    return builder.as_markup()


def _build_subscription_prompt_text(channels: list[dict], language: str) -> str:
    text = get_text("must_subscribe", language) + "\n\n"
    for channel in channels:
        title = channel.get("title") or "Channel"
        url = channel.get("url")
        if url:
            text += f"• <a href=\"{url}\">{title}</a>\n"
    return text


class SubscriptionCheckMiddleware(BaseMiddleware):
    """Middleware that enforces mandatory channel subscriptions using a
    live Telegram membership check (bot.get_chat_member), gated by an
    admin-controlled on/off toggle stored in app_settings."""

    def __init__(self, db, bot=None):
        self.db = db
        # `bot` is resolved lazily from app_context if not injected, so this
        # middleware keeps working regardless of how main.py wires it up.
        if bot is None:
            from app_context import bot as app_bot
            bot = app_bot
        self.bot = bot
        self.sub_manager = SubscriptionManager(db, bot=bot)

    async def __call__(self, handler, event, data: dict):
        if isinstance(event, types.CallbackQuery) and event.data == CHECK_SUBSCRIPTION_CALLBACK:
            await self._handle_check_button(event)
            return

        if not isinstance(event, types.Message):
            return await handler(event, data)

        user_id = event.from_user.id
        chat_type = event.chat.type

        # Skip checks for group chats and excluded commands
        if chat_type != "private":
            return await handler(event, data)

        message_text = event.text or ""
        if any(message_text.startswith(cmd) for cmd in _EXCLUDED_COMMANDS):
            return await handler(event, data)

        try:
            if not await self.sub_manager.is_mandatory_subscription_feature_enabled():
                return await handler(event, data)

            not_subscribed = await self.sub_manager.get_unsubscribed_channels(user_id)
            if not_subscribed:
                user_language = await self._get_user_language(user_id)
                await event.reply(
                    _build_subscription_prompt_text(not_subscribed, user_language),
                    reply_markup=build_subscription_prompt_keyboard(
                        not_subscribed, user_language
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                return

        except Exception as e:
            logging.error(f"Subscription check failed for {user_id}: {e}")
            # Fail open: don't block bot usage if the check itself errors.

        return await handler(event, data)

    async def _handle_check_button(self, query: types.CallbackQuery) -> None:
        user_id = query.from_user.id
        user_language = await self._get_user_language(user_id)
        try:
            if not await self.sub_manager.is_mandatory_subscription_feature_enabled():
                await query.answer(get_text("saved", user_language))
                try:
                    await query.message.delete()
                except Exception:
                    pass
                return

            not_subscribed = await self.sub_manager.get_unsubscribed_channels(user_id)
            if not_subscribed:
                await query.answer(
                    "❌ Hali barcha kanallarga obuna bo'lmadingiz"
                    if user_language == "uz"
                    else "❌ You haven't joined all channels yet",
                    show_alert=True,
                )
                try:
                    await query.message.edit_text(
                        _build_subscription_prompt_text(not_subscribed, user_language),
                        reply_markup=build_subscription_prompt_keyboard(
                            not_subscribed, user_language
                        ),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception:
                    pass
                return

            await query.answer(
                "✅ Obuna tasdiqlandi!" if user_language == "uz" else "✅ Subscription confirmed!",
                show_alert=True,
            )
            try:
                await query.message.delete()
            except Exception:
                pass
        except Exception as e:
            logging.error(f"Subscription re-check failed for {user_id}: {e}")
            await query.answer(
                get_text("error", user_language), show_alert=True
            )

    async def _get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        try:
            settings = await self.db.user_settings(user_id)
            return settings.get("language", "uz")
        except Exception:
            return "uz"
