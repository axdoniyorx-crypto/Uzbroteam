from aiogram import types, Router, F
from aiogram.filters import Command
from services.localization import get_text
from keyboards.language_keyboards import language_choice_keyboard, welcome_keyboard
import handlers.user as user_mod
from services.logger import logger as logging
logging = logging.bind(service="language_handler")
router = Router()


@router.callback_query(F.data == "show_language_choice")
async def callback_show_language_choice(query: types.CallbackQuery):
    """Show language choice when the user taps the 🌐 Til / Language button."""
    text = get_text("choose_language", "uz")
    try:
        await query.message.edit_text(
            text,
            reply_markup=language_choice_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await query.message.answer(
            text,
            reply_markup=language_choice_keyboard(),
            parse_mode="HTML",
        )
    await query.answer()


@router.callback_query(F.data.startswith("set_language:"))
async def callback_set_language(query: types.CallbackQuery):
    """Handle language selection"""
    user_id = query.from_user.id
    language = query.data.split(":")[1]
    if language not in ["uz", "en"]:
        language = "uz"
    # Store language directly in user record using upsert_user
    try:
        await user_mod.db.upsert_user(
            user_id=user_id,
            user_name=query.from_user.first_name,
            user_username=query.from_user.username,
            language=language,
        )
        logging.event("language_set", user_id=user_id, language=language)
    except Exception as e:
        logging.error(f"Failed to set language: {e}")

    # Show the real /start welcome message (with working buttons) in the
    # chosen language, instead of the separate legacy welcome text/keyboard.
    import messages as bm
    import keyboards as kb
    from handlers.utils import get_bot_username

    bot_username = await get_bot_username(user_mod.bot)
    welcome_text = await bm.welcome_message(language=language)
    try:
        await query.message.edit_text(
            welcome_text,
            reply_markup=kb.start_keyboard(bot_username, ref_user_id=user_id),
            parse_mode="HTML",
        )
    except Exception:
        await query.message.answer(
            welcome_text,
            reply_markup=kb.start_keyboard(bot_username, ref_user_id=user_id),
            parse_mode="HTML",
        )
    await query.answer(
        get_text("saved", language),
        show_alert=False,
    )
