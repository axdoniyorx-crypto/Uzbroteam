from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.localization import get_text


def _t(uz: str, en: str, language: str) -> str:
    return uz if language == "uz" else en


def admin_main_panel_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    """Main admin panel keyboard"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📊 " + _t("Statistika", "Statistics", language), callback_data="admin_stats")
    builder.button(text="📬 " + _t("Xabar yuborish", "Broadcast", language), callback_data="admin_broadcast")
    builder.button(text="👥 " + _t("Obunalarni boshqarish", "Manage Subscriptions", language), callback_data="admin_subscriptions")
    builder.button(text="📣 " + _t("Ixtiyoriy kanal", "Optional Channel", language), callback_data="admin_optional_channel")
    builder.button(text="💾 " + _t("Xotira / Storage", "Storage", language), callback_data="admin_storage")
    builder.button(text="👤 " + _t("Foydalanuvchilar", "Users", language), callback_data="admin_users")
    builder.button(text="🚫 " + _t("Bloklangan foydalanuvchilar", "Banned Users", language), callback_data="admin_banned_users")
    builder.button(text="⚙️ " + _t("Bot sozlamalari", "Bot Settings", language), callback_data="admin_bot_settings")
    builder.button(text="📝 " + _t("Loglar va xatolar", "Logs & Errors", language), callback_data="admin_logs")
    builder.button(text="🔄 " + _t("Botni boshqarish", "Bot Control", language), callback_data="admin_bot_control")
    builder.button(text="🛠️ " + _t("Mailing / Loglar (eski panel)", "Mailing / Logs (legacy panel)", language), callback_data="admin_legacy_panel")
    builder.button(text=get_text("btn_back", language), callback_data="back_to_main")

    builder.adjust(2, 2, 2, 2, 2, 1, 1)
    return builder.as_markup()


def return_to_admin_main_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Mandatory subscription management
# ---------------------------------------------------------------------------

def subscription_management_keyboard(
    language: str = "uz", mandatory_enabled: bool = True
) -> types.InlineKeyboardMarkup:
    """Mandatory subscription management keyboard"""
    builder = InlineKeyboardBuilder()

    toggle_text = _t(
        "✅ Majburiy obuna: Yoqilgan" if mandatory_enabled else "🚫 Majburiy obuna: O'chirilgan",
        "✅ Mandatory subscription: ON" if mandatory_enabled else "🚫 Mandatory subscription: OFF",
        language,
    )
    builder.button(text=toggle_text, callback_data="admin_toggle_mandatory_subscription")
    builder.button(text="➕ " + _t("Kanal qo'shish", "Add Channel", language), callback_data="admin_add_channel:mandatory")
    builder.button(text="📋 " + _t("Kanallar ro'yxati", "Channel List", language), callback_data="admin_list_channels:mandatory")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")

    builder.adjust(1)
    return builder.as_markup()


def channel_list_keyboard(
    channels: list[dict], subscription_type: str, language: str = "uz"
) -> types.InlineKeyboardMarkup:
    """List channels with per-channel manage buttons."""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        title = channel.get("title") or str(channel.get("channel_id"))
        status_icon = "✅" if channel.get("is_active", True) else "🚫"
        builder.button(
            text=f"{status_icon} {title}",
            callback_data=f"admin_channel_manage:{subscription_type}:{channel['channel_id']}",
        )
    back_target = "admin_subscriptions" if subscription_type == "mandatory" else "admin_optional_channel"
    builder.button(text=get_text("btn_back", language), callback_data=back_target)
    builder.adjust(1)
    return builder.as_markup()


def channel_manage_keyboard(
    channel_id: int, subscription_type: str, is_active: bool, language: str = "uz"
) -> types.InlineKeyboardMarkup:
    """Manage a single channel: edit, delete, toggle on/off."""
    builder = InlineKeyboardBuilder()
    toggle_text = _t("🚫 O'chirish (OFF)", "🚫 Turn OFF", language) if is_active else _t("✅ Yoqish (ON)", "✅ Turn ON", language)
    builder.button(text=toggle_text, callback_data=f"admin_channel_toggle:{subscription_type}:{channel_id}")
    builder.button(text="✏️ " + _t("Tahrirlash", "Edit", language), callback_data=f"admin_channel_edit:{subscription_type}:{channel_id}")
    builder.button(text="🗑️ " + _t("O'chirish", "Delete", language), callback_data=f"admin_channel_delete:{subscription_type}:{channel_id}")
    builder.button(
        text=get_text("btn_back", language),
        callback_data=f"admin_list_channels:{subscription_type}",
    )
    builder.adjust(1)
    return builder.as_markup()


def channel_delete_confirm_keyboard(
    channel_id: int, subscription_type: str, language: str = "uz"
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ " + _t("Ha, o'chirish", "Yes, delete", language),
        callback_data=f"admin_channel_delete_confirm:{subscription_type}:{channel_id}",
    )
    builder.button(
        text="✖️ " + _t("Bekor qilish", "Cancel", language),
        callback_data=f"admin_channel_manage:{subscription_type}:{channel_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Optional (promo) channel management
# ---------------------------------------------------------------------------

def optional_channel_keyboard(
    language: str = "uz", enabled: bool = True
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = _t(
        "✅ Ixtiyoriy kanal: Yoqilgan" if enabled else "🚫 Ixtiyoriy kanal: O'chirilgan",
        "✅ Optional channel: ON" if enabled else "🚫 Optional channel: OFF",
        language,
    )
    builder.button(text=toggle_text, callback_data="admin_toggle_optional_channel")
    builder.button(text="➕ " + _t("Link qo'shish", "Add Link", language), callback_data="admin_add_channel:optional")
    builder.button(text="📋 " + _t("Linklar ro'yxati", "Link List", language), callback_data="admin_list_channels:optional")
    builder.button(text="👁️ " + _t("Preview", "Preview", language), callback_data="admin_optional_channel_preview")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------

def broadcast_management_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    """Broadcast management keyboard"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✍️ " + _t("Yangi xabar", "New Message", language), callback_data="admin_broadcast_new")
    builder.button(text="📬 " + _t("Qoralamalar", "Drafts", language), callback_data="admin_broadcast_drafts")
    builder.button(text="✅ " + _t("Yuborilganlar", "Sent", language), callback_data="admin_broadcast_sent")
    builder.button(text="⏰ " + _t("Rejalashtirilgan", "Scheduled", language), callback_data="admin_broadcast_scheduled")
    builder.button(text="📊 " + _t("Broadcast statistikasi", "Broadcast Stats", language), callback_data="admin_broadcast_stats")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")

    builder.adjust(1)
    return builder.as_markup()


def broadcast_audience_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=_t("Hammaga", "Everyone", language), callback_data="broadcast_target:all")
    builder.button(text=_t("Faqat shaxsiy chatlar", "DM only", language), callback_data="broadcast_target:dm")
    builder.button(text=_t("Faqat guruhlar", "Groups only", language), callback_data="broadcast_target:groups")
    builder.button(text="✖️ " + get_text("btn_cancel", language), callback_data="admin_broadcast")
    builder.adjust(1)
    return builder.as_markup()


def broadcast_confirm_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 " + _t("Hozir yuborish", "Send now", language), callback_data="broadcast_send_now")
    builder.button(text="⏰ " + _t("Rejalashtirish", "Schedule", language), callback_data="broadcast_schedule")
    builder.button(text="❌ " + _t("Bekor qilish", "Cancel", language), callback_data="admin_broadcast")
    builder.adjust(1)
    return builder.as_markup()


def broadcast_item_list_keyboard(
    items: list[dict], *, action_prefix: str, back_callback: str, language: str = "uz"
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        preview = item.get("message_text", "")[:30]
        builder.button(
            text=f"#{item['id']} {preview}",
            callback_data=f"{action_prefix}:{item['id']}",
        )
    builder.button(text=get_text("btn_back", language), callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()


def broadcast_draft_manage_keyboard(broadcast_id: int, language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 " + _t("Yuborish", "Send", language), callback_data=f"admin_broadcast_send:{broadcast_id}")
    builder.button(text="❌ " + _t("Bekor qilish", "Cancel", language), callback_data=f"admin_broadcast_cancel:{broadcast_id}")
    builder.button(text=get_text("btn_back", language), callback_data="admin_broadcast_drafts")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def storage_management_keyboard(
    language: str = "uz", auto_cleanup_enabled: bool = True
) -> types.InlineKeyboardMarkup:
    """Storage management keyboard"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📊 " + _t("Storage statistikasi", "Storage Stats", language), callback_data="admin_storage_stats")
    builder.button(text="🗑️ " + _t("Eski fayllarni o'chirish", "Delete Old Files", language), callback_data="admin_cleanup_old")
    builder.button(text="⚡ " + _t("Hajm bo'yicha tozalash", "Cleanup by Size", language), callback_data="admin_cleanup_size")
    builder.button(text="🧹 " + _t("Cache tozalash", "Clear Cache", language), callback_data="admin_cleanup_cache")
    toggle_text = _t(
        "✅ Avtomatik tozalash: Yoqilgan" if auto_cleanup_enabled else "🚫 Avtomatik tozalash: O'chirilgan",
        "✅ Auto cleanup: ON" if auto_cleanup_enabled else "🚫 Auto cleanup: OFF",
        language,
    )
    builder.button(text=toggle_text, callback_data="admin_toggle_auto_cleanup")
    builder.button(text="⏱️ " + _t("Saqlanish vaqti", "Retention TTL", language), callback_data="admin_set_ttl")
    builder.button(text="💾 " + _t("Maksimal hajm", "Max Size", language), callback_data="admin_set_max_size")
    builder.button(text="🕐 " + _t("Keyingi tozalash", "Next Cleanup", language), callback_data="admin_next_cleanup")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")

    builder.adjust(1)
    return builder.as_markup()


def ttl_options_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for hours in (6, 12, 24, 48, 72, 168):
        label = f"{hours}" + _t(" soat", "h", language)
        builder.button(text=label, callback_data=f"admin_ttl_set:{hours}")
    builder.button(text=get_text("btn_back", language), callback_data="admin_storage")
    builder.adjust(3)
    return builder.as_markup()


def max_size_options_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for size_mb in (512, 1024, 2048, 4096, 8192):
        label = f"{size_mb} MB" if size_mb < 1024 else f"{size_mb // 1024} GB"
        builder.button(text=label, callback_data=f"admin_max_size_set:{size_mb}")
    builder.button(text=get_text("btn_back", language), callback_data="admin_storage")
    builder.adjust(3)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def users_management_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 " + _t("Foydalanuvchi qidirish", "Search User", language), callback_data="admin_search_user")
    builder.button(text="📊 " + _t("Statistika", "Stats", language), callback_data="admin_users_stats")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


def user_profile_keyboard(user_id: int, is_banned: bool, language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_banned:
        builder.button(text="✅ " + _t("Blokdan chiqarish", "Unban", language), callback_data=f"admin_unban_user:{user_id}")
    else:
        builder.button(text="🚫 " + _t("Bloklash", "Ban", language), callback_data=f"admin_ban_user:{user_id}")
    builder.button(text=get_text("btn_back", language), callback_data="admin_users")
    builder.adjust(1)
    return builder.as_markup()


def banned_users_keyboard(users: list, language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user in users:
        label = user.user_username or user.user_name or str(user.user_id)
        builder.button(text=f"🚫 {label}", callback_data=f"admin_user_profile:{user.user_id}")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Bot settings
# ---------------------------------------------------------------------------

def bot_settings_keyboard(
    language: str = "uz", *, bot_enabled: bool = True,
) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔒 " + _t("Majburiy obuna", "Mandatory Subscription", language),
        callback_data="admin_subscriptions",
    )
    builder.button(
        text="📣 " + _t("Ixtiyoriy kanal", "Optional Channel", language),
        callback_data="admin_optional_channel",
    )
    builder.button(
        text="💾 " + _t("Storage sozlamalari", "Storage Settings", language),
        callback_data="admin_storage",
    )
    bot_toggle_text = _t(
        "🟢 Bot: Yoqilgan" if bot_enabled else "🔴 Bot: O'chirilgan",
        "🟢 Bot: ON" if bot_enabled else "🔴 Bot: OFF",
        language,
    )
    builder.button(text=bot_toggle_text, callback_data="admin_toggle_bot_enabled")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


def bot_disable_confirm_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ " + _t("Ha, o'chirish", "Yes, disable", language),
        callback_data="admin_bot_disable_confirm",
    )
    builder.button(
        text="✖️ " + _t("Bekor qilish", "Cancel", language),
        callback_data="admin_bot_settings",
    )
    builder.adjust(1)
    return builder.as_markup()


# ---------------------------------------------------------------------------
# Logs / bot control
# ---------------------------------------------------------------------------

def logs_management_keyboard(language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 " + _t("Loglarni yuklab olish", "Download Logs", language), callback_data="download_log")
    builder.button(text="🗑️ " + _t("Loglarni tozalash", "Clear Logs", language), callback_data="delete_log")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


def bot_control_keyboard(language: str = "uz", bot_enabled: bool = True) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = _t(
        "🔴 Botni o'chirish" if bot_enabled else "🟢 Botni yoqish",
        "🔴 Disable Bot" if bot_enabled else "🟢 Enable Bot",
        language,
    )
    builder.button(text=toggle_text, callback_data="admin_toggle_bot_enabled")
    builder.button(text="📊 " + _t("Ish holati", "Runtime status", language), callback_data="admin_ops")
    builder.button(text=get_text("btn_back", language), callback_data="admin_main")
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard_simple(callback_data: str = "admin_main", language: str = "uz") -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✖️ " + get_text("btn_cancel", language), callback_data=callback_data)
    return builder.as_markup()
