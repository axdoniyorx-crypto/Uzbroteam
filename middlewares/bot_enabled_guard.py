from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from services.logger import logger as logging

logging = logging.bind(service="bot_enabled_guard")

_ALWAYS_ALLOWED_COMMANDS = ("/admin",)

_DISABLED_TEXT = "🔧 Bot vaqtincha texnik ishlar uchun o'chirilgan. Birozdan keyin qayta urinib ko'ring."


class BotEnabledGuardMiddleware(BaseMiddleware):
    """Blocks all non-admin usage when the admin has toggled the bot off
    via the admin panel's Bot Control section. Admins can always still
    reach /admin so they can turn it back on."""

    def __init__(self, db):
        self.db = db

    async def __call__(self, handler, event, data: dict):
        is_message = isinstance(event, types.Message)
        is_callback = isinstance(event, types.CallbackQuery)
        if not is_message and not is_callback:
            return await handler(event, data)

        user = event.from_user
        from config import ADMINS_UID

        if user and user.id in ADMINS_UID:
            return await handler(event, data)

        if is_message:
            text = event.text or ""
            if any(text.startswith(cmd) for cmd in _ALWAYS_ALLOWED_COMMANDS):
                return await handler(event, data)

        try:
            bot_enabled = await self.db.is_bot_enabled()
        except Exception as exc:
            logging.error("Failed to check bot_enabled flag: %s", exc)
            return await handler(event, data)

        if bot_enabled:
            return await handler(event, data)

        if is_message and event.chat.type == "private":
            await event.answer(_DISABLED_TEXT)
        elif is_callback:
            await event.answer(_DISABLED_TEXT, show_alert=True)
        return None
