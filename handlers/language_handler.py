from aiogram import types, Router, F
from aiogram.filters import Command
from services.localization import get_text
from keyboards.language_keyboards import language_choice_keyboard, welcome_keyboard
import handlers.user as user_mod
from services.logger import logger as logging
logging = logging.bind(service="language_handler")
router = Router()
@router.message(Command("start"))
async def cmd_start_language_choice(message: types.Message):
    """Show language choice on /start"""
    user_id = message.from_user.id
    # Update user info
    await user_mod.update_info(message)
    # Send language choice
    text = get_text("choose_language", "uz")
    await message.reply(
        text,
        reply_markup=language_choice_keyboard(),
        parse_mode="HTML",
    )
    logging.event("language_choice_shown", user_id=user_id)


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
    # Show welcome message in chosen language
    welcome_text = get_text("welcome", language)
    await query.message.edit_text(
        welcome_text,
        reply_markup=welcome_keyboard(language),
        parse_mode="HTML",
    )
    await query.answer(
        get_text("saved", language),
        show_alert=False,
    )
