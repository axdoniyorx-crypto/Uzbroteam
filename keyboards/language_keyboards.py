from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.localization import get_text

def language_choice_keyboard() -> types.InlineKeyboardMarkup:
    """Keyboard for language selection"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("language_uzbek", "uz"),
        callback_data="set_language:uz"
    )
    builder.button(
        text=get_text("language_english", "en"),
        callback_data="set_language:en"
    )
    builder.adjust(1)
    return builder.as_markup()

def welcome_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    """Welcome message keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_inline", language),
        switch_inline_query_current_chat=""
    )
    builder.button(
        text=get_text("btn_settings", language),
        callback_data="settings"
    )
    builder.button(
        text=get_text("btn_help", language),
        callback_data="help"
    )
    builder.button(
        text=get_text("btn_share", language),
        switch_inline_query="bot"
    )
    builder.adjust(2)
    return builder.as_markup()

def subscription_check_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    """Keyboard to show subscription status"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_back", language),
        callback_data="back_to_main"
    )
    builder.adjust(1)
    return builder.as_markup()
