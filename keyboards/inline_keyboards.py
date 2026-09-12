from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import quote


def start_keyboard(bot_username: str | None = None, ref_user_id: int | None = None) -> InlineKeyboardMarkup:
    """Start command keyboard with inline, settings, share and group add buttons."""
    username = bot_username or "birbosbot"
    base_link = f"https://t.me/{username}"

    share_text = "Instagram, TikTok, YouTube va boshqalar uchun tezkor yuklab oluvchi bot!"
    share_url = f"https://t.me/share/url?url={quote(base_link)}&text={quote(share_text)}"
    add_to_group_url = f"https://t.me/{username}?startgroup=true"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡ Inline sinash", switch_inline_query_current_chat=""),
                InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="back_to_settings"),
            ],
            [
                InlineKeyboardButton(text="🚀 Botni ulashish", url=share_url),
                InlineKeyboardButton(text="➕ Guruhga qo'shish", url=add_to_group_url),
            ],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Simple cancel button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="cancel_action")
    return builder.as_markup()


def mailing_audience_keyboard() -> InlineKeyboardMarkup:
    """Choose mailing audience: DM only, groups only, or all."""
    buttons = [
        [InlineKeyboardButton(text="👤 Faqat shaxsiy chatlar", callback_data="mailing_target:dm")],
        [InlineKeyboardButton(text="🏘 Faqat guruhlar", callback_data="mailing_target:groups")],
        [InlineKeyboardButton(text="🌐 Barchasi (DM + Guruhlar)", callback_data="mailing_target:all")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_number(value: int) -> str | None:
    """Format large numbers (1000 -> 1K, 1000000 -> 1M, etc)."""
    if value is None:
        return None
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


FIELD_CATEGORY_MAP = {
    "video_quality": "media",
    "as_document": "media",
    "audio_format": "media",
    "captions": "appearance",
    "info_buttons": "appearance",
    "audio_button": "appearance",
    "file_button": "appearance",
    "url_button": "appearance",
    "delete_message": "chat",
}


def return_settings_categories_keyboard() -> InlineKeyboardMarkup:
    """Main settings categories: Media, Appearance, Chat."""
    buttons = [
        [InlineKeyboardButton(text="🎬 Media va sifat", callback_data="settings_cat:media")],
        [InlineKeyboardButton(text="🎨 Ko'rinish va tugmalar", callback_data="settings_cat:appearance")],
        [InlineKeyboardButton(text="💬 Chat va tozalash", callback_data="settings_cat:chat")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def return_category_settings_keyboard(category: str) -> InlineKeyboardMarkup:
    """Settings for a specific category (media, appearance, or chat)."""
    if category == "media":
        fields = [
            ("🎬 Video sifati", "video_quality"),
            ("📄 Fayl sifatida yuborish", "as_document"),
            ("🎵 Audio format", "audio_format"),
        ]
    elif category == "appearance":
        fields = [
            ("📝 Tavsiflar", "captions"),
            ("ℹ️ Ma'lumot tugmalari", "info_buttons"),
            ("🎧 MP3 tugmasi", "audio_button"),
            ("📄 Fayl tugmasi", "file_button"),
            ("🔗 URL tugmasi", "url_button"),
        ]
    else:  # chat
        fields = [
            ("🗑️ Xabarlarni o'chirish", "delete_message"),
        ]

    buttons = [
        [InlineKeyboardButton(text=text, callback_data=f"settings:{field}")]
        for text, field in fields
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Kategoriyalarga qaytish", callback_data="back_to_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def return_field_keyboard(field: str, value: str | None) -> InlineKeyboardMarkup:
    """Keyboard for editing a specific settings field."""
    val = (value or "").strip().lower()
    cat = FIELD_CATEGORY_MAP.get(field, "media")
    back_cb = f"settings_cat:{cat}"

    if field == "video_quality":
        current = val or "best"
        opt_best = "✅ 🏆 Eng yaxshi (1080p+)" if current == "best" else "🏆 Eng yaxshi (1080p+)"
        opt_bal = "✅ ⚖️ Muvozanatli (720p)" if current == "balanced" else "⚖️ Muvozanatli (720p)"
        opt_saver = "✅ ⚡ Trafik tejash (480p)" if current == "saver" else "⚡ Trafik tejash (480p)"

        buttons = [
            [InlineKeyboardButton(text=opt_best, callback_data="setting:video_quality:best")],
            [InlineKeyboardButton(text=opt_bal, callback_data="setting:video_quality:balanced")],
            [InlineKeyboardButton(text=opt_saver, callback_data="setting:video_quality:saver")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_cb)],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    if field == "audio_format":
        current = val or "mp3"
        opt_mp3 = "✅ 🎧 MP3 Audio" if current == "mp3" else "🎧 MP3 Audio"
        opt_m4a = "✅ 📱 M4A (AAC)" if current == "m4a" else "📱 M4A (AAC)"
        opt_best = "✅ 🎼 FLAC / Original" if current == "best" else "🎼 FLAC / Original"

        buttons = [
            [InlineKeyboardButton(text=opt_mp3, callback_data="setting:audio_format:mp3")],
            [InlineKeyboardButton(text=opt_m4a, callback_data="setting:audio_format:m4a")],
            [InlineKeyboardButton(text=opt_best, callback_data="setting:audio_format:best")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_cb)],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    # Toggle on/off for boolean settings
    is_enabled = val == "on"
    status_text = "🟢 Hozir YOQILGAN" if is_enabled else "🔴 Hozir O'CHIRILGAN"
    next_value = "off" if is_enabled else "on"
    action_text = "🔴 O'CHIRISH" if is_enabled else "🟢 YOQISH"

    buttons = [
        [InlineKeyboardButton(text=status_text, callback_data="noop")],
        [InlineKeyboardButton(text=action_text, callback_data=f"setting:{field}:{next_value}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=back_cb)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def return_settings_keyboard() -> InlineKeyboardMarkup:
    """Return main settings keyboard."""
    return return_settings_categories_keyboard()


def stats_keyboard(current_period: str = "Week", mode: str = "total") -> InlineKeyboardMarkup:
    """Stats view keyboard: period (Week/Month/Year) and view mode (total/split)."""
    periods = ["Week", "Month", "Year"]
    period_labels = {"Week": "Hafta", "Month": "Oy", "Year": "Yil"}
    period_buttons = [
        InlineKeyboardButton(
            text=f"[{period_labels[period]}]" if period == current_period else period_labels[period],
            callback_data=f"stats:{period}:{mode}",
        )
        for period in periods
    ]

    toggle_target = "split" if mode == "total" else "total"
    toggle_label = "Ko'rinish: Platforma bo'yicha" if mode == "total" else "Ko'rinish: Umumiy"

    buttons = [
        period_buttons,
        [InlineKeyboardButton(text=toggle_label, callback_data=f"stats:{current_period}:{toggle_target}")],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel main keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="🩺 Holat", callback_data="admin_ops"),
            InlineKeyboardButton(text="📦 Resurslar", callback_data="admin_runtime_storage"),
        ],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh")],
        [
            InlineKeyboardButton(text="👥 Faol foydalanuvchilarni tekshirish", callback_data="check_active_users"),
            InlineKeyboardButton(text="🏘 Guruhlarni tekshirish", callback_data="check_active_groups"),
        ],
        [InlineKeyboardButton(text="📬 Xabar tarqatish", callback_data="send_to_all")],
        [InlineKeyboardButton(text="✉️ Chat ID orqali xabar", callback_data="message_chat_id")],
        [InlineKeyboardButton(text="👋 Salomlashish xabarini sozlash", callback_data="admin_welcome_message")],
        [
            InlineKeyboardButton(text="📄 Logni ko'rish", callback_data="download_log"),
            InlineKeyboardButton(text="🗑️ Logni o'chirish", callback_data="delete_log"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def welcome_message_settings_keyboard(is_custom: bool) -> InlineKeyboardMarkup:
    """Keyboard for the welcome-message settings screen."""
    buttons = [
        [InlineKeyboardButton(text="✏️ Matnni o'zgartirish", callback_data="admin_welcome_message_edit")],
    ]
    if is_custom:
        buttons.append(
            [InlineKeyboardButton(text="♻️ Standartga qaytarish", callback_data="admin_welcome_message_reset")]
        )
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_detail_keyboard(refresh_callback: str) -> InlineKeyboardMarkup:
    """Admin detail view with refresh and back buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data=refresh_callback)],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")],
        ]
    )


def downloads_admin_keyboard(can_cleanup: bool = True, refresh_callback: str = "admin_downloads") -> InlineKeyboardMarkup:
    """Admin downloads view keyboard with optional cleanup button."""
    buttons = [[InlineKeyboardButton(text="🔄 Yangilash", callback_data=refresh_callback)]]
    if can_cleanup:
        buttons.append([InlineKeyboardButton(text="🧹 Yuklamalarni tozalash", callback_data="admin_cleanup_downloads")])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def return_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Simple back to admin button."""
    back_button = [
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=back_button)


def start_private_chat_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Button to open bot in private chat from group."""
    url = f"https://t.me/{bot_username}?start=from_group"
    button = [[InlineKeyboardButton(text="💬 Bot chatini ochish", url=url)]]
    return InlineKeyboardMarkup(inline_keyboard=button)


def return_audio_download_keyboard(platform: str, url: str) -> InlineKeyboardMarkup:
    """Audio download button for a specific platform/URL.

    Uses a short opaque token instead of the raw URL in callback_data,
    since Telegram rejects callback_data over 64 bytes and real media URLs
    routinely exceed that once a prefix is added.
    """
    from services.platforms.audio_callback_tokens import register_audio_url

    audio_button = [
        [InlineKeyboardButton(text="🎧 MP3 yuklab olish", callback_data=f"{platform}_audio_{register_audio_url(url)}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=audio_button)


def inline_send_video_keyboard(token: str) -> InlineKeyboardMarkup:
    """Send video inline button for TikTok."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Videoni inline yuborish", callback_data=f"inline:tiktok:{token}")]
        ]
    )


def inline_send_media_keyboard(text: str, callback_data: str) -> InlineKeyboardMarkup:
    """Generic send media inline button with custom text and callback."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=callback_data)]
        ]
    )


def return_user_info_keyboard(nickname: str, followers: int | None, videos: int | None, likes: int | None, url: str) -> InlineKeyboardMarkup:
    """User profile info display: nickname link + stats."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text=nickname, url=url))

    row1 = []
    if followers is not None:
        row1.append(
            InlineKeyboardButton(
                text=f"👥 {format_number(followers)}",
                callback_data=f"followers_{format_number(followers)}",
            )
        )
    if videos is not None:
        row1.append(
            InlineKeyboardButton(
                text=f"🎬 {format_number(videos)}",
                callback_data=f"videos_{format_number(videos)}",
            )
        )
    if likes is not None:
        row1.append(
            InlineKeyboardButton(
                text=f"❤️ {format_number(likes)}",
                callback_data=f"likes_{format_number(likes)}",
            )
        )

    if row1:
        builder.row(*row1)

    return builder.as_markup()


def return_video_info_keyboard(
    views: int | None,
    likes: int | None,
    comments: int | None,
    shares: int | None,
    music_play_url: str | None,
    video_url: str | None,
    user_settings: dict,
    audio_callback_data: str | None = None,
    file_callback_data: str | None = None,
) -> InlineKeyboardMarkup:
    """Video info display: stats (if enabled), audio/file download, and URL buttons."""
    builder = InlineKeyboardBuilder()

    if user_settings.get("info_buttons") == "on":
        row1 = []
        if views is not None:
            formatted_views = format_number(views)
            row1.append(
                InlineKeyboardButton(
                    text=f"👁 {formatted_views}",
                    callback_data=f"views_{formatted_views}",
                )
            )
        if likes is not None:
            formatted_likes = format_number(likes)
            row1.append(
                InlineKeyboardButton(
                    text=f"❤️ {formatted_likes}",
                    callback_data=f"likes_{formatted_likes}",
                )
            )
        if comments is not None:
            formatted_comments = format_number(comments)
            row1.append(
                InlineKeyboardButton(
                    text=f"💬 {formatted_comments}",
                    callback_data=f"comments_{formatted_comments}",
                )
            )
        if shares is not None:
            formatted_shares = format_number(shares)
            row1.append(
                InlineKeyboardButton(
                    text=f"🔁 {formatted_shares}",
                    callback_data=f"shares_{formatted_shares}",
                )
            )

        if row1:
            builder.row(*row1)

    if user_settings.get("audio_button") == "on" and audio_callback_data:
        builder.row(InlineKeyboardButton(text="🎧 MP3 yuklab olish", callback_data=audio_callback_data))

    if (
        user_settings.get("file_button") == "on"
        and user_settings.get("as_document") != "on"
        and file_callback_data
    ):
        builder.row(InlineKeyboardButton(text="📄 Faylni yuklab olish", callback_data=file_callback_data))

    if user_settings.get("url_button") == "on" and video_url:
        builder.row(InlineKeyboardButton(text="🔗 URL", url=video_url))

    return builder.as_markup()


def _stats_keyboard_legacy_bottom(current_period: str = "Week", mode: str = "total") -> InlineKeyboardMarkup:
    """Legacy stats keyboard (dot-prefixed periods, toggle label). Unused but kept for compatibility."""
    periods = ["Week", "Month", "Year"]
    period_labels = {"Week": "Hafta", "Month": "Oy", "Year": "Yil"}
    period_buttons = [
        InlineKeyboardButton(
            text=f"{'· ' if period == current_period else ''}{period_labels[period]}",
            callback_data=f"stats:{period}:{mode}",
        )
        for period in periods
    ]

    toggle_target = "split" if mode == "total" else "total"
    toggle_label = f"Bo'lingan ko'rinish: {'Yoqilgan' if mode == 'split' else 'O' + chr(0x02bb) + 'chirilgan'}"

    buttons = [
        period_buttons,
        [InlineKeyboardButton(text=toggle_label, callback_data=f"stats:{current_period}:{toggle_target}")],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
