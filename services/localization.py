from messages.locales import en, uz
from services.logger import logger as logging

logging = logging.bind(service="localization")

LOCALES = {
    "uz": uz,
    "en": en,
}

DEFAULT_LANGUAGE = "uz"


def get_text(key: str, language: str | None = None) -> str:
    """Get localized text message by key and language"""
    if language is None:
        language = DEFAULT_LANGUAGE

    locale = LOCALES.get(language, LOCALES[DEFAULT_LANGUAGE])
    text = locale.get_text(key)

    if text == key:
        logging.warning(f"Translation key not found: {key} (lang={language})")

    return text


def get_language_from_user(user_language_code: str | None) -> str:
    """Get application language from Telegram user language code"""
    if not user_language_code:
        return DEFAULT_LANGUAGE

    user_lang = user_language_code.lower().split("-")[0]

    if user_lang == "uz":
        return "uz"
    elif user_lang == "en":
        return "en"

    return DEFAULT_LANGUAGE
