from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_optional_channel_keyboard(
    channels: list[dict], language: str = "uz"
) -> types.InlineKeyboardMarkup:
    """Build a keyboard with links to optional (non-mandatory) promo
    channels. Joining these channels is never required to use the bot;
    this is purely a promotional nudge shown alongside normal usage."""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        title = channel.get("title") or "Channel"
        url = channel.get("url")
        if url:
            builder.button(text=f"📣 {title}", url=url)
    builder.adjust(1)
    return builder.as_markup()
