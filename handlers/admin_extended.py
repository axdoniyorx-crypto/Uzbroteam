import re
from datetime import datetime, timedelta, timezone

from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.logger import logger as logging
from services.localization import get_text
from services.subscription import SubscriptionManager
from services.broadcast_service import BroadcastService
from services.storage_manager import StorageManager
from services.scheduler_service import run_manual_cleanup_cycle
from services.runtime.stats import get_runtime_snapshot
from keyboards.admin_keyboards import (
    admin_main_panel_keyboard,
    subscription_management_keyboard,
    channel_list_keyboard,
    channel_manage_keyboard,
    channel_delete_confirm_keyboard,
    optional_channel_keyboard,
    broadcast_management_keyboard,
    broadcast_audience_keyboard,
    broadcast_confirm_keyboard,
    broadcast_item_list_keyboard,
    broadcast_draft_manage_keyboard,
    storage_management_keyboard,
    ttl_options_keyboard,
    max_size_options_keyboard,
    users_management_keyboard,
    user_profile_keyboard,
    banned_users_keyboard,
    bot_settings_keyboard,
    bot_disable_confirm_keyboard,
    logs_management_keyboard,
    bot_control_keyboard,
    cancel_keyboard_simple,
    return_to_admin_main_keyboard,
)
import handlers.user as user_mod
import config

logging = logging.bind(service="admin_handler")

router = Router()

ADMIN_IDS = [
    int(id_str) for id_str in (
        config.ADMINS_UID
        if hasattr(config, 'ADMINS_UID')
        else []
    )
]


async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


async def _get_user_language(user_id: int) -> str:
    """Get user's preferred language"""
    try:
        settings = await user_mod.db.user_settings(user_id)
        return settings.get("language", "uz")
    except Exception:
        return "uz"


def _sub_manager() -> SubscriptionManager:
    from app_context import bot as app_bot
    return SubscriptionManager(user_mod.db, bot=app_bot)


def _broadcast_service() -> BroadcastService:
    from app_context import bot as app_bot
    return BroadcastService(app_bot, user_mod.db)


# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------

class ChannelForm(StatesGroup):
    waiting_for_channel_input = State()
    waiting_for_channel_edit = State()


class BroadcastForm(StatesGroup):
    waiting_for_text = State()
    waiting_for_schedule_time = State()


class UserSearchForm(StatesGroup):
    waiting_for_query = State()


class StorageSettingForm(StatesGroup):
    waiting_for_ttl = State()
    waiting_for_max_size = State()


async def _deny(query: types.CallbackQuery) -> bool:
    if not await is_admin(query.from_user.id):
        await query.answer(get_text("no_permission", "uz"), show_alert=True)
        return True
    return False


# ---------------------------------------------------------------------------
# Main admin panel
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin_panel(message: types.Message):
    """Admin panel command"""
    if not await is_admin(message.from_user.id):
        await message.reply(get_text("no_permission", "uz"))
        return

    user_language = await _get_user_language(message.from_user.id)
    text = get_text("admin_panel", user_language)

    await message.reply(
        text,
        reply_markup=admin_main_panel_keyboard(user_language),
        parse_mode="HTML",
    )
    logging.event("admin_panel_opened", admin_id=message.from_user.id)


@router.callback_query(F.data == "back_to_main")
async def callback_back_to_main_menu(query: types.CallbackQuery, state: FSMContext):
    """Leave the admin panel; show the regular bot welcome message."""
    await state.clear()
    user_language = await _get_user_language(query.from_user.id)
    import messages as bm
    import keyboards as kb
    from handlers.utils import get_bot_username
    from app_context import bot as app_bot

    bot_username = await get_bot_username(app_bot)
    welcome_text = await bm.welcome_message()
    try:
        await query.message.edit_text(
            welcome_text,
            reply_markup=kb.start_keyboard(bot_username, ref_user_id=query.from_user.id),
            parse_mode="HTML",
        )
    except Exception:
        await query.message.answer(
            welcome_text,
            reply_markup=kb.start_keyboard(bot_username, ref_user_id=query.from_user.id),
            parse_mode="HTML",
        )
    await query.answer()


@router.callback_query(F.data == "admin_main")
async def callback_back_to_admin(query: types.CallbackQuery, state: FSMContext):
    """Back to main admin panel"""
    await state.clear()
    user_language = await _get_user_language(query.from_user.id)
    text = get_text("admin_panel", user_language)

    await query.message.edit_text(
        text,
        reply_markup=admin_main_panel_keyboard(user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(query: types.CallbackQuery):
    """Show overall bot statistics"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    counts = await user_mod.db.get_community_stats()
    runtime_snapshot = get_runtime_snapshot()

    text = (
        "<b>📊 Statistika</b>\n\n"
        f"👤 Shaxsiy chatlar: <b>{counts.get('dm_total', 0)}</b>\n"
        f"   ├ Faol: {counts.get('dm_active', 0)}\n"
        f"   ├ Nofaol: {counts.get('dm_inactive', 0)}\n"
        f"   └ Bloklangan: {counts.get('dm_banned', 0)}\n\n"
        f"👥 Guruhlar: <b>{counts.get('groups_total', 0)}</b>\n"
        f"   ├ Faol: {counts.get('groups_active', 0)}\n"
        f"   └ Umumiy qamrov: {counts.get('total_reach', 0)}\n\n"
        f"⬇️ Joriy sessiyada yuklab olishlar: <b>{runtime_snapshot.total_downloads}</b>\n"
        f"   ├ Video: {runtime_snapshot.total_videos}\n"
        f"   ├ Audio: {runtime_snapshot.total_audio}\n"
        f"   └ Boshqa: {runtime_snapshot.total_other}\n"
    ) if user_language == "uz" else (
        "<b>📊 Statistics</b>\n\n"
        f"👤 DM chats: <b>{counts.get('dm_total', 0)}</b>\n"
        f"   ├ Active: {counts.get('dm_active', 0)}\n"
        f"   ├ Inactive: {counts.get('dm_inactive', 0)}\n"
        f"   └ Banned: {counts.get('dm_banned', 0)}\n\n"
        f"👥 Groups: <b>{counts.get('groups_total', 0)}</b>\n"
        f"   ├ Active: {counts.get('groups_active', 0)}\n"
        f"   └ Total reach: {counts.get('total_reach', 0)}\n\n"
        f"⬇️ Downloads this session: <b>{runtime_snapshot.total_downloads}</b>\n"
        f"   ├ Video: {runtime_snapshot.total_videos}\n"
        f"   ├ Audio: {runtime_snapshot.total_audio}\n"
        f"   └ Other: {runtime_snapshot.total_other}\n"
    )

    await query.message.edit_text(
        text, reply_markup=return_to_admin_main_keyboard(user_language), parse_mode="HTML"
    )
    await query.answer()


# ---------------------------------------------------------------------------
# Mandatory subscription management
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_subscriptions")
async def callback_subscriptions_menu(query: types.CallbackQuery):
    """Subscription management menu"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    mandatory_enabled = await sub_manager.is_mandatory_subscription_feature_enabled()

    await query.message.edit_text(
        "<b>🔒 Majburiy obuna</b>" if user_language == "uz" else "<b>🔒 Mandatory Subscription</b>",
        reply_markup=subscription_management_keyboard(user_language, mandatory_enabled),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_toggle_mandatory_subscription")
async def callback_toggle_mandatory_subscription(query: types.CallbackQuery):
    """Toggle the global mandatory-subscription feature on/off"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()

    currently_enabled = await sub_manager.is_mandatory_subscription_feature_enabled()
    new_state = not currently_enabled
    await sub_manager.set_mandatory_subscription_feature_enabled(new_state)

    await query.message.edit_text(
        "<b>🔒 Majburiy obuna</b>" if user_language == "uz" else "<b>🔒 Mandatory Subscription</b>",
        reply_markup=subscription_management_keyboard(user_language, new_state),
        parse_mode="HTML",
    )

    if user_language == "uz":
        alert_text = "✅ Majburiy obuna yoqildi" if new_state else "🚫 Majburiy obuna o'chirildi"
    else:
        alert_text = "✅ Mandatory subscription enabled" if new_state else "🚫 Mandatory subscription disabled"

    await query.answer(alert_text, show_alert=True)
    logging.event(
        "mandatory_subscription_toggled",
        admin_id=query.from_user.id,
        enabled=new_state,
    )


@router.callback_query(F.data.startswith("admin_list_channels:"))
async def callback_list_channels(query: types.CallbackQuery):
    """List channels (mandatory or optional)"""
    if await _deny(query):
        return

    subscription_type = query.data.split(":", 1)[1]
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    channels = await sub_manager.get_channels(subscription_type=subscription_type, only_active=False)

    if not channels:
        empty_text = (
            "Hozircha kanallar yo'q." if user_language == "uz" else "No channels yet."
        )
        back_target = "admin_subscriptions" if subscription_type == "mandatory" else "admin_optional_channel"
        await query.message.edit_text(
            empty_text,
            reply_markup=return_to_admin_main_keyboard(user_language)
            if back_target == "admin_main"
            else channel_list_keyboard([], subscription_type, user_language),
        )
        await query.answer()
        return

    title = (
        "<b>📋 Majburiy kanallar</b>" if subscription_type == "mandatory" else "<b>📋 Ixtiyoriy kanallar</b>"
    ) if user_language == "uz" else (
        "<b>📋 Mandatory Channels</b>" if subscription_type == "mandatory" else "<b>📋 Optional Channels</b>"
    )

    await query.message.edit_text(
        title,
        reply_markup=channel_list_keyboard(channels, subscription_type, user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_channel_manage:"))
async def callback_channel_manage(query: types.CallbackQuery):
    """Show a single channel's manage menu"""
    if await _deny(query):
        return

    _, subscription_type, channel_id_str = query.data.split(":", 2)
    channel_id = int(channel_id_str)
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    channel = await sub_manager.get_channel(channel_id)

    if not channel:
        await query.answer(
            "Kanal topilmadi" if user_language == "uz" else "Channel not found",
            show_alert=True,
        )
        return

    text = (
        f"<b>{channel['title']}</b>\n"
        f"ID: <code>{channel['channel_id']}</code>\n"
        f"Link: {channel['url']}\n"
        f"Holat: {'✅ Faol' if channel['is_active'] else '🚫 Faol emas'}"
    ) if user_language == "uz" else (
        f"<b>{channel['title']}</b>\n"
        f"ID: <code>{channel['channel_id']}</code>\n"
        f"Link: {channel['url']}\n"
        f"Status: {'✅ Active' if channel['is_active'] else '🚫 Inactive'}"
    )

    await query.message.edit_text(
        text,
        reply_markup=channel_manage_keyboard(
            channel_id, subscription_type, channel["is_active"], user_language
        ),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_channel_toggle:"))
async def callback_channel_toggle(query: types.CallbackQuery):
    """Toggle a single channel's active flag"""
    if await _deny(query):
        return

    _, subscription_type, channel_id_str = query.data.split(":", 2)
    channel_id = int(channel_id_str)
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    channel = await sub_manager.get_channel(channel_id)
    if not channel:
        await query.answer("Not found", show_alert=True)
        return

    new_state = not channel["is_active"]
    await sub_manager.set_channel_active(channel_id, new_state)
    await query.answer(get_text("saved", user_language))

    updated = await sub_manager.get_channel(channel_id)
    await query.message.edit_reply_markup(
        reply_markup=channel_manage_keyboard(
            channel_id, subscription_type, updated["is_active"], user_language
        )
    )


@router.callback_query(F.data.startswith("admin_channel_delete:"))
async def callback_channel_delete_prompt(query: types.CallbackQuery):
    """Ask for delete confirmation"""
    if await _deny(query):
        return
    _, subscription_type, channel_id_str = query.data.split(":", 2)
    channel_id = int(channel_id_str)
    user_language = await _get_user_language(query.from_user.id)

    confirm_text = (
        "Ushbu kanalni o'chirishni tasdiqlaysizmi?" if user_language == "uz"
        else "Confirm channel deletion?"
    )
    await query.message.edit_text(
        confirm_text,
        reply_markup=channel_delete_confirm_keyboard(channel_id, subscription_type, user_language),
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_channel_delete_confirm:"))
async def callback_channel_delete_confirm(query: types.CallbackQuery):
    """Actually delete the channel"""
    if await _deny(query):
        return
    _, subscription_type, channel_id_str = query.data.split(":", 2)
    channel_id = int(channel_id_str)
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    await sub_manager.delete_channel(channel_id)

    logging.event("channel_deleted_via_admin", admin_id=query.from_user.id, channel_id=channel_id)
    await query.answer(get_text("saved", user_language), show_alert=True)

    channels = await sub_manager.get_channels(subscription_type=subscription_type, only_active=False)
    title = "<b>📋 Kanallar</b>" if user_language == "uz" else "<b>📋 Channels</b>"
    await query.message.edit_text(
        title,
        reply_markup=channel_list_keyboard(channels, subscription_type, user_language),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_channel_edit:"))
async def callback_channel_edit_prompt(query: types.CallbackQuery, state: FSMContext):
    """Prompt admin to send a new title/url pair for the channel"""
    if await _deny(query):
        return
    _, subscription_type, channel_id_str = query.data.split(":", 2)
    channel_id = int(channel_id_str)
    user_language = await _get_user_language(query.from_user.id)

    await state.set_state(ChannelForm.waiting_for_channel_edit)
    await state.update_data(channel_id=channel_id, subscription_type=subscription_type)

    prompt = (
        "Yangi nom va linkni yuboring, quyidagi formatda:\n<code>Nom | https://t.me/link</code>"
        if user_language == "uz"
        else "Send the new title and link in this format:\n<code>Title | https://t.me/link</code>"
    )
    await query.message.edit_text(
        prompt,
        reply_markup=cancel_keyboard_simple(f"admin_channel_manage:{subscription_type}:{channel_id}", user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.message(ChannelForm.waiting_for_channel_edit)
async def process_channel_edit(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    subscription_type = data.get("subscription_type", "mandatory")
    user_language = await _get_user_language(message.from_user.id)

    parts = (message.text or "").split("|")
    if len(parts) != 2:
        await message.reply(
            "Noto'g'ri format. Namuna: <code>Nom | https://t.me/link</code>"
            if user_language == "uz"
            else "Invalid format. Example: <code>Title | https://t.me/link</code>",
            parse_mode="HTML",
        )
        return

    title, url = parts[0].strip(), parts[1].strip()
    sub_manager = _sub_manager()
    await sub_manager.update_channel(channel_id, title=title, url=url)
    await state.clear()

    await message.answer(
        get_text("saved", user_language),
        reply_markup=return_to_admin_main_keyboard(user_language),
    )
    logging.event("channel_edited", admin_id=message.from_user.id, channel_id=channel_id)


@router.callback_query(F.data.startswith("admin_add_channel:"))
async def callback_add_channel_prompt(query: types.CallbackQuery, state: FSMContext):
    """Prompt admin to forward a channel post or send channel details"""
    if await _deny(query):
        return

    subscription_type = query.data.split(":", 1)[1]
    user_language = await _get_user_language(query.from_user.id)

    await state.set_state(ChannelForm.waiting_for_channel_input)
    await state.update_data(subscription_type=subscription_type)

    prompt = (
        "Kanal ma'lumotlarini quyidagi formatda yuboring:\n"
        "<code>channel_id | Nom | https://t.me/link</code>\n\n"
        "Masalan: <code>-1001234567890 | Mening kanalim | https://t.me/mychannel</code>\n\n"
        "channel_id ni bilish uchun kanaldagi biror xabarni botga forward qiling "
        "yoki @userinfobot orqali oling. Bot kanalda admin bo'lishi shart."
    ) if user_language == "uz" else (
        "Send channel info in this format:\n"
        "<code>channel_id | Title | https://t.me/link</code>\n\n"
        "Example: <code>-1001234567890 | My Channel | https://t.me/mychannel</code>\n\n"
        "The bot must be an admin in that channel."
    )
    await query.message.edit_text(
        prompt,
        reply_markup=cancel_keyboard_simple(
            "admin_subscriptions" if subscription_type == "mandatory" else "admin_optional_channel",
            user_language,
        ),
        parse_mode="HTML",
    )
    await query.answer()


@router.message(ChannelForm.waiting_for_channel_input)
async def process_add_channel(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    subscription_type = data.get("subscription_type", "mandatory")
    user_language = await _get_user_language(message.from_user.id)

    parts = (message.text or "").split("|")
    if len(parts) != 3:
        await message.reply(
            "Noto'g'ri format. Namuna: <code>-1001234567890 | Nom | https://t.me/link</code>"
            if user_language == "uz"
            else "Invalid format. Example: <code>-1001234567890 | Title | https://t.me/link</code>",
            parse_mode="HTML",
        )
        return

    channel_id_str, title, url = (p.strip() for p in parts)
    try:
        channel_id = int(channel_id_str)
    except ValueError:
        await message.reply(
            "channel_id butun son bo'lishi kerak." if user_language == "uz" else "channel_id must be an integer."
        )
        return

    sub_manager = _sub_manager()
    await sub_manager.add_channel(
        channel_id=channel_id, title=title, url=url, subscription_type=subscription_type
    )
    await state.clear()

    await message.answer(
        get_text("saved", user_language),
        reply_markup=return_to_admin_main_keyboard(user_language),
    )
    logging.event(
        "channel_added_via_admin",
        admin_id=message.from_user.id,
        channel_id=channel_id,
        type=subscription_type,
    )


# ---------------------------------------------------------------------------
# Optional channel
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_optional_channel")
async def callback_optional_channel_menu(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    enabled = await sub_manager.is_optional_channel_feature_enabled()

    await query.message.edit_text(
        "<b>📣 Ixtiyoriy kanal</b>" if user_language == "uz" else "<b>📣 Optional Channel</b>",
        reply_markup=optional_channel_keyboard(user_language, enabled),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_toggle_optional_channel")
async def callback_toggle_optional_channel(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    new_state = not await sub_manager.is_optional_channel_feature_enabled()
    await sub_manager.set_optional_channel_feature_enabled(new_state)

    await query.message.edit_reply_markup(
        reply_markup=optional_channel_keyboard(user_language, new_state)
    )
    await query.answer(get_text("saved", user_language))


@router.callback_query(F.data == "admin_optional_channel_preview")
async def callback_optional_channel_preview(query: types.CallbackQuery):
    """Show users what the optional channel promo looks like"""
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    sub_manager = _sub_manager()
    channels = await sub_manager.get_channels(subscription_type="optional")

    if not channels:
        await query.answer(
            "Ixtiyoriy kanallar yo'q" if user_language == "uz" else "No optional channels",
            show_alert=True,
        )
        return

    from keyboards.optional_channel import build_optional_channel_keyboard

    preview_text = (
        "👇 Bizning qo'shimcha kanalimizga a'zo bo'ling!" if user_language == "uz"
        else "👇 Join our extra channel!"
    )
    await query.message.answer(
        preview_text,
        reply_markup=build_optional_channel_keyboard(channels, user_language),
    )
    await query.answer()


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_broadcast")
async def callback_broadcast_menu(query: types.CallbackQuery, state: FSMContext):
    """Broadcast management menu"""
    if await _deny(query):
        return
    await state.clear()

    user_language = await _get_user_language(query.from_user.id)
    await query.message.edit_text(
        "<b>📬 Xabar yuborish</b>" if user_language == "uz" else "<b>📬 Broadcast</b>",
        reply_markup=broadcast_management_keyboard(user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_broadcast_new")
async def callback_broadcast_new(query: types.CallbackQuery, state: FSMContext):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    await state.set_state(BroadcastForm.waiting_for_text)

    prompt = (
        "Yubormoqchi bo'lgan xabar matnini yuboring:" if user_language == "uz"
        else "Send the message text you want to broadcast:"
    )
    await query.message.edit_text(
        prompt, reply_markup=cancel_keyboard_simple("admin_broadcast", user_language)
    )
    await query.answer()


@router.message(BroadcastForm.waiting_for_text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return

    user_language = await _get_user_language(message.from_user.id)
    await state.update_data(message_text=message.text, image_url=None)

    preview = (
        f"<b>Ko'rinishi:</b>\n\n{message.text}\n\n"
        "Auditoriyani tanlang:"
    ) if user_language == "uz" else (
        f"<b>Preview:</b>\n\n{message.text}\n\n"
        "Choose audience:"
    )
    await message.answer(
        preview, reply_markup=broadcast_audience_keyboard(user_language), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("broadcast_target:"))
async def callback_broadcast_target(query: types.CallbackQuery, state: FSMContext):
    if await _deny(query):
        return
    target_type = query.data.split(":", 1)[1]
    user_language = await _get_user_language(query.from_user.id)
    await state.update_data(target_type=target_type)

    confirm_text = (
        "Xabarni qanday yuborishni xohlaysiz?" if user_language == "uz"
        else "How would you like to send this?"
    )
    await query.message.edit_text(
        confirm_text, reply_markup=broadcast_confirm_keyboard(user_language)
    )
    await query.answer()


@router.callback_query(F.data == "broadcast_send_now")
async def callback_broadcast_send_now(query: types.CallbackQuery, state: FSMContext):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    data = await state.get_data()
    message_text = data.get("message_text")
    target_type = data.get("target_type", "all")
    image_url = data.get("image_url")

    if not message_text:
        await query.answer("Xatolik: matn topilmadi" if user_language == "uz" else "Error: no text", show_alert=True)
        return

    broadcast_id = await user_mod.db.create_broadcast(
        message_text=message_text,
        created_by=query.from_user.id,
        target_type=target_type,
        image_url=image_url,
    )
    await state.clear()

    await query.message.edit_text(
        "🚀 Yuborilmoqda..." if user_language == "uz" else "🚀 Sending...",
    )
    await query.answer()

    service = _broadcast_service()
    result = await service.send_broadcast(broadcast_id, target_type=target_type)

    done_text = (
        f"✅ Yuborildi!\n📤 Yetkazildi: {result['sent']}\n❌ Xato: {result['failed']}"
        if user_language == "uz"
        else f"✅ Sent!\n📤 Delivered: {result['sent']}\n❌ Failed: {result['failed']}"
    )
    await query.message.answer(
        done_text, reply_markup=return_to_admin_main_keyboard(user_language)
    )


@router.callback_query(F.data == "broadcast_schedule")
async def callback_broadcast_schedule_prompt(query: types.CallbackQuery, state: FSMContext):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    await state.set_state(BroadcastForm.waiting_for_schedule_time)

    prompt = (
        "Qachon yuborilsin? Soat va daqiqani yuboring (masalan: <code>18:30</code>), "
        "bugungi kun uchun rejalashtiriladi. Agar vaqt allaqachon o'tgan bo'lsa, ertaga yuboriladi."
        if user_language == "uz"
        else "When should it be sent? Send time as <code>HH:MM</code> (today, or tomorrow if already past)."
    )
    await query.message.edit_text(
        prompt,
        reply_markup=cancel_keyboard_simple("admin_broadcast", user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.message(BroadcastForm.waiting_for_schedule_time)
async def process_broadcast_schedule_time(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return

    user_language = await _get_user_language(message.from_user.id)
    match = re.match(r"^(\d{1,2}):(\d{2})$", (message.text or "").strip())
    if not match:
        await message.reply(
            "Noto'g'ri format. Masalan: <code>18:30</code>" if user_language == "uz"
            else "Invalid format. Example: <code>18:30</code>",
            parse_mode="HTML",
        )
        return

    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour < 24 and 0 <= minute < 60):
        await message.reply(
            "Noto'g'ri vaqt." if user_language == "uz" else "Invalid time."
        )
        return

    now = datetime.now(timezone.utc)
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if scheduled <= now:
        scheduled += timedelta(days=1)

    data = await state.get_data()
    message_text = data.get("message_text")
    target_type = data.get("target_type", "all")
    image_url = data.get("image_url")

    broadcast_id = await user_mod.db.create_broadcast(
        message_text=message_text,
        created_by=message.from_user.id,
        target_type=target_type,
        image_url=image_url,
    )
    await user_mod.db.schedule_broadcast(broadcast_id, scheduled)
    await state.clear()

    confirm = (
        f"⏰ Xabar {scheduled.strftime('%Y-%m-%d %H:%M UTC')} da yuborish uchun rejalashtirildi."
        if user_language == "uz"
        else f"⏰ Message scheduled for {scheduled.strftime('%Y-%m-%d %H:%M UTC')}."
    )
    await message.answer(confirm, reply_markup=return_to_admin_main_keyboard(user_language))
    logging.event("broadcast_scheduled_via_admin", admin_id=message.from_user.id, broadcast_id=broadcast_id)


@router.callback_query(F.data == "admin_broadcast_drafts")
async def callback_broadcast_drafts(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    drafts = await user_mod.db.list_broadcasts(status="draft")

    if not drafts:
        await query.message.edit_text(
            "Qoralamalar yo'q." if user_language == "uz" else "No drafts.",
            reply_markup=return_to_admin_main_keyboard(user_language),
        )
        await query.answer()
        return

    await query.message.edit_text(
        "<b>📬 Qoralamalar</b>" if user_language == "uz" else "<b>📬 Drafts</b>",
        reply_markup=broadcast_item_list_keyboard(
            drafts, action_prefix="admin_broadcast_draft", back_callback="admin_broadcast", language=user_language
        ),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_broadcast_draft:"))
async def callback_broadcast_draft_view(query: types.CallbackQuery):
    if await _deny(query):
        return
    broadcast_id = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    broadcast = await user_mod.db.get_broadcast(broadcast_id)
    if not broadcast:
        await query.answer("Not found", show_alert=True)
        return

    await query.message.edit_text(
        broadcast["message_text"],
        reply_markup=broadcast_draft_manage_keyboard(broadcast_id, user_language),
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_broadcast_send:"))
async def callback_broadcast_send_draft(query: types.CallbackQuery):
    if await _deny(query):
        return
    broadcast_id = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    broadcast = await user_mod.db.get_broadcast(broadcast_id)
    if not broadcast:
        await query.answer("Not found", show_alert=True)
        return

    await query.answer("🚀 " + ("Yuborilmoqda..." if user_language == "uz" else "Sending..."))
    service = _broadcast_service()
    result = await service.send_broadcast(broadcast_id, target_type=broadcast["target_type"])

    done_text = (
        f"✅ Yuborildi!\n📤 Yetkazildi: {result['sent']}\n❌ Xato: {result['failed']}"
        if user_language == "uz"
        else f"✅ Sent!\n📤 Delivered: {result['sent']}\n❌ Failed: {result['failed']}"
    )
    await query.message.edit_text(done_text, reply_markup=return_to_admin_main_keyboard(user_language))


@router.callback_query(F.data.startswith("admin_broadcast_cancel:"))
async def callback_broadcast_cancel_draft(query: types.CallbackQuery):
    if await _deny(query):
        return
    broadcast_id = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    await user_mod.db.cancel_broadcast(broadcast_id)
    await query.answer(get_text("saved", user_language))
    await query.message.edit_text(
        "❌ Bekor qilindi." if user_language == "uz" else "❌ Cancelled.",
        reply_markup=return_to_admin_main_keyboard(user_language),
    )


@router.callback_query(F.data == "admin_broadcast_sent")
async def callback_broadcast_sent(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    sent = await user_mod.db.list_broadcasts(status="sent")

    if not sent:
        await query.message.edit_text(
            "Yuborilgan xabarlar yo'q." if user_language == "uz" else "No sent messages.",
            reply_markup=return_to_admin_main_keyboard(user_language),
        )
        await query.answer()
        return

    lines = ["<b>✅ Yuborilganlar</b>" if user_language == "uz" else "<b>✅ Sent</b>", ""]
    for item in sent:
        lines.append(
            f"#{item['id']} — {item['message_text']} "
            f"(✅{item['sent_count']} ❌{item['failed_count']})"
        )
    await query.message.edit_text(
        "\n".join(lines),
        reply_markup=return_to_admin_main_keyboard(user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_broadcast_scheduled")
async def callback_broadcast_scheduled(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    scheduled = await user_mod.db.list_broadcasts(status="scheduled")

    if not scheduled:
        await query.message.edit_text(
            "Rejalashtirilgan xabarlar yo'q." if user_language == "uz" else "No scheduled messages.",
            reply_markup=return_to_admin_main_keyboard(user_language),
        )
        await query.answer()
        return

    await query.message.edit_text(
        "<b>⏰ Rejalashtirilgan</b>" if user_language == "uz" else "<b>⏰ Scheduled</b>",
        reply_markup=broadcast_item_list_keyboard(
            scheduled, action_prefix="admin_broadcast_draft", back_callback="admin_broadcast", language=user_language
        ),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_broadcast_stats")
async def callback_broadcast_stats(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    stats = await user_mod.db.get_broadcast_overview_stats()

    text = (
        "<b>📊 Broadcast statistikasi</b>\n\n"
        f"Jami xabarlar: <b>{stats['total']}</b>\n"
        f"Yuborilgan: {stats['sent']}\n"
        f"Qoralama: {stats['draft']}\n"
        f"Rejalashtirilgan: {stats['scheduled']}\n\n"
        f"Umumiy yetkazilgan: {stats['total_sent_count']}\n"
        f"Umumiy xato: {stats['total_failed_count']}"
    ) if user_language == "uz" else (
        "<b>📊 Broadcast Stats</b>\n\n"
        f"Total messages: <b>{stats['total']}</b>\n"
        f"Sent: {stats['sent']}\n"
        f"Draft: {stats['draft']}\n"
        f"Scheduled: {stats['scheduled']}\n\n"
        f"Total delivered: {stats['total_sent_count']}\n"
        f"Total failed: {stats['total_failed_count']}"
    )
    await query.message.edit_text(
        text, reply_markup=return_to_admin_main_keyboard(user_language), parse_mode="HTML"
    )
    await query.answer()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_storage")
async def callback_storage_menu(query: types.CallbackQuery):
    """Storage management menu"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        "<b>💾 Xotira boshqaruvi</b>" if user_language == "uz" else "<b>💾 Storage Management</b>",
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_storage_stats")
async def callback_storage_stats(query: types.CallbackQuery):
    """Show storage statistics"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    storage_manager = StorageManager()
    stats = storage_manager.get_storage_stats()

    stats_text = (
        "<b>💾 Xotira statistikasi</b>\n\n"
        f"📁 Jami fayllar: {stats['total_files']}\n"
        f"💾 Umumiy hajm: {stats['total_size_mb']} MB\n"
    ) if user_language == "uz" else (
        "<b>💾 Storage Statistics</b>\n\n"
        f"📁 Total files: {stats['total_files']}\n"
        f"💾 Total size: {stats['total_size_mb']} MB\n"
    )

    if stats['oldest_file_date']:
        stats_text += f"📅 Eng eski fayl: {stats['oldest_file_date']}\n" if user_language == "uz" else f"📅 Oldest file: {stats['oldest_file_date']}\n"

    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        stats_text,
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_cleanup_old")
async def callback_cleanup_old(query: types.CallbackQuery):
    """Cleanup old files"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    ttl_hours = await user_mod.db.get_auto_cleanup_ttl_hours()
    storage_manager = StorageManager()
    result = storage_manager.cleanup_old_files(hours_old=ttl_hours)

    cleanup_text = (
        "<b>✅ Tozalash tugallandi</b>\n\n"
        f"🗑️ O'chirilgan fayllar: {result['deleted_files']}\n"
        f"💾 Ozod qilingan: {result['freed_mb']} MB\n"
    ) if user_language == "uz" else (
        "<b>✅ Cleanup Completed</b>\n\n"
        f"🗑️ Deleted files: {result['deleted_files']}\n"
        f"💾 Freed: {result['freed_mb']} MB\n"
    )

    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        cleanup_text,
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    await query.answer(get_text("saved", user_language))
    logging.event("cleanup_executed", admin_id=query.from_user.id, freed_mb=result['freed_mb'])


@router.callback_query(F.data == "admin_cleanup_size")
async def callback_cleanup_size(query: types.CallbackQuery):
    """Cleanup by size limit"""
    if await _deny(query):
        return

    user_language = await _get_user_language(query.from_user.id)
    max_size_mb = await user_mod.db.get_auto_cleanup_max_size_mb()
    storage_manager = StorageManager()
    result = storage_manager.cleanup_by_size_limit(max_size_mb)

    cleanup_text = (
        "<b>⚡ Hajm bo'yicha tozalash tugallandi</b>\n\n"
        f"🗑️ O'chirilgan fayllar: {result['deleted_files']}\n"
        f"💾 Ozod qilingan: {result['freed_mb']} MB\n"
        f"📏 Limit: {max_size_mb} MB\n"
    ) if user_language == "uz" else (
        "<b>⚡ Cleanup by Size Completed</b>\n\n"
        f"🗑️ Deleted files: {result['deleted_files']}\n"
        f"💾 Freed: {result['freed_mb']} MB\n"
        f"📏 Limit: {max_size_mb} MB\n"
    )

    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        cleanup_text,
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    await query.answer(get_text("saved", user_language))
    logging.event("cleanup_by_size_executed", admin_id=query.from_user.id, freed_mb=result['freed_mb'])


@router.callback_query(F.data == "admin_cleanup_cache")
async def callback_cleanup_cache(query: types.CallbackQuery):
    """Clear the DB-backed file_id cache (downloaded_files table)"""
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    deleted = await user_mod.db.cleanup_expired_files(max_age_days=0)

    text = (
        f"<b>🧹 Cache tozalandi</b>\n\nO'chirilgan yozuvlar: {deleted}"
        if user_language == "uz"
        else f"<b>🧹 Cache cleared</b>\n\nDeleted entries: {deleted}"
    )
    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        text,
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    await query.answer(get_text("saved", user_language))
    logging.event("cache_cleanup_executed", admin_id=query.from_user.id, deleted=deleted)


@router.callback_query(F.data == "admin_toggle_auto_cleanup")
async def callback_toggle_auto_cleanup(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    new_state = not await user_mod.db.is_auto_cleanup_enabled()
    await user_mod.db.set_auto_cleanup_enabled(new_state)

    await query.message.edit_reply_markup(
        reply_markup=storage_management_keyboard(user_language, new_state)
    )
    await query.answer(get_text("saved", user_language))
    logging.event("auto_cleanup_toggled", admin_id=query.from_user.id, enabled=new_state)


@router.callback_query(F.data == "admin_set_ttl")
async def callback_set_ttl_menu(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    current = await user_mod.db.get_auto_cleanup_ttl_hours()
    text = (
        f"Joriy saqlanish vaqti: <b>{current} soat</b>\nYangisini tanlang:"
        if user_language == "uz"
        else f"Current retention: <b>{current}h</b>\nChoose a new value:"
    )
    await query.message.edit_text(
        text, reply_markup=ttl_options_keyboard(user_language), parse_mode="HTML"
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_ttl_set:"))
async def callback_ttl_set(query: types.CallbackQuery):
    if await _deny(query):
        return
    hours = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    await user_mod.db.set_auto_cleanup_ttl_hours(hours)
    await query.answer(get_text("saved", user_language), show_alert=True)

    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        "<b>💾 Xotira boshqaruvi</b>" if user_language == "uz" else "<b>💾 Storage Management</b>",
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    logging.event("auto_cleanup_ttl_set", admin_id=query.from_user.id, hours=hours)


@router.callback_query(F.data == "admin_set_max_size")
async def callback_set_max_size_menu(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    current = await user_mod.db.get_auto_cleanup_max_size_mb()
    text = (
        f"Joriy maksimal hajm: <b>{current} MB</b>\nYangisini tanlang:"
        if user_language == "uz"
        else f"Current max size: <b>{current} MB</b>\nChoose a new value:"
    )
    await query.message.edit_text(
        text, reply_markup=max_size_options_keyboard(user_language), parse_mode="HTML"
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_max_size_set:"))
async def callback_max_size_set(query: types.CallbackQuery):
    if await _deny(query):
        return
    size_mb = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    await user_mod.db.set_auto_cleanup_max_size_mb(size_mb)
    await query.answer(get_text("saved", user_language), show_alert=True)

    auto_cleanup_enabled = await user_mod.db.is_auto_cleanup_enabled()
    await query.message.edit_text(
        "<b>💾 Xotira boshqaruvi</b>" if user_language == "uz" else "<b>💾 Storage Management</b>",
        reply_markup=storage_management_keyboard(user_language, auto_cleanup_enabled),
        parse_mode="HTML",
    )
    logging.event("auto_cleanup_max_size_set", admin_id=query.from_user.id, size_mb=size_mb)


@router.callback_query(F.data == "admin_next_cleanup")
async def callback_next_cleanup(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    schedule = await user_mod.db.get_auto_cleanup_schedule()
    last_run = schedule.get("last_run_at") or ("Hali ishlamagan" if user_language == "uz" else "Never run yet")
    next_run = schedule.get("next_run_at") or ("Noma'lum" if user_language == "uz" else "Unknown")

    text = (
        f"🕐 <b>Tozalash jadvali</b>\n\nOxirgi ishga tushish: {last_run}\nKeyingi ishga tushish: {next_run}"
        if user_language == "uz"
        else f"🕐 <b>Cleanup schedule</b>\n\nLast run: {last_run}\nNext run: {next_run}"
    )
    await query.answer(text[:200], show_alert=True)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_users")
async def callback_users_menu(query: types.CallbackQuery, state: FSMContext):
    if await _deny(query):
        return
    await state.clear()
    user_language = await _get_user_language(query.from_user.id)
    await query.message.edit_text(
        "<b>👤 Foydalanuvchilar</b>" if user_language == "uz" else "<b>👤 Users</b>",
        reply_markup=users_management_keyboard(user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_users_stats")
async def callback_users_stats(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    counts = await user_mod.db.get_community_stats()

    text = (
        f"👤 Jami: {counts.get('dm_total', 0)}\n"
        f"✅ Faol: {counts.get('dm_active', 0)}\n"
        f"💤 Nofaol: {counts.get('dm_inactive', 0)}\n"
        f"🚫 Bloklangan: {counts.get('dm_banned', 0)}"
    ) if user_language == "uz" else (
        f"👤 Total: {counts.get('dm_total', 0)}\n"
        f"✅ Active: {counts.get('dm_active', 0)}\n"
        f"💤 Inactive: {counts.get('dm_inactive', 0)}\n"
        f"🚫 Banned: {counts.get('dm_banned', 0)}"
    )
    await query.message.edit_text(
        text, reply_markup=users_management_keyboard(user_language)
    )
    await query.answer()


@router.callback_query(F.data == "admin_search_user")
async def callback_search_user_prompt(query: types.CallbackQuery, state: FSMContext):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    await state.set_state(UserSearchForm.waiting_for_query)

    prompt = (
        "Foydalanuvchi ID, username yoki ismini yuboring:" if user_language == "uz"
        else "Send the user ID, username, or name:"
    )
    await query.message.edit_text(
        prompt, reply_markup=cancel_keyboard_simple("admin_users", user_language)
    )
    await query.answer()


@router.message(UserSearchForm.waiting_for_query)
async def process_user_search(message: types.Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await state.clear()
        return

    user_language = await _get_user_language(message.from_user.id)
    query_text = (message.text or "").strip()
    await state.clear()

    results = await user_mod.db.search_users(query_text, limit=5)
    if not results:
        await message.answer(
            "Hech kim topilmadi." if user_language == "uz" else "No users found.",
            reply_markup=return_to_admin_main_keyboard(user_language),
        )
        return

    for row in results:
        is_banned = (row.status or "") == "ban"
        text = (
            f"👤 <b>{row.user_name or 'N/A'}</b>\n"
            f"Username: @{row.user_username}\n" if row.user_username else f"👤 <b>{row.user_name or 'N/A'}</b>\n"
        )
        text += (
            f"ID: <code>{row.user_id}</code>\n"
            f"Til: {row.language or 'n/a'}\n"
            f"Holat: {'🚫 Bloklangan' if is_banned else '✅ Faol'}"
        ) if user_language == "uz" else (
            f"ID: <code>{row.user_id}</code>\n"
            f"Language: {row.language or 'n/a'}\n"
            f"Status: {'🚫 Banned' if is_banned else '✅ Active'}"
        )
        await message.answer(
            text,
            reply_markup=user_profile_keyboard(row.user_id, is_banned, user_language),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("admin_user_profile:"))
async def callback_user_profile(query: types.CallbackQuery):
    if await _deny(query):
        return
    target_id = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    info = await user_mod.db.get_user_info(target_id)
    if not info:
        await query.answer("Not found", show_alert=True)
        return

    is_banned = (info[2] or "") == "ban"
    text = (
        f"👤 <b>{info[0] or 'N/A'}</b>\nID: <code>{target_id}</code>\n"
        f"Holat: {'🚫 Bloklangan' if is_banned else '✅ Faol'}"
    ) if user_language == "uz" else (
        f"👤 <b>{info[0] or 'N/A'}</b>\nID: <code>{target_id}</code>\n"
        f"Status: {'🚫 Banned' if is_banned else '✅ Active'}"
    )
    await query.message.edit_text(
        text,
        reply_markup=user_profile_keyboard(target_id, is_banned, user_language),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data.startswith("admin_ban_user:"))
async def callback_ban_user(query: types.CallbackQuery):
    if await _deny(query):
        return
    target_id = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    await user_mod.db.ban_user(target_id)
    await query.answer(get_text("saved", user_language), show_alert=True)
    await query.message.edit_reply_markup(
        reply_markup=user_profile_keyboard(target_id, True, user_language)
    )
    logging.event("user_banned", admin_id=query.from_user.id, target_id=target_id)


@router.callback_query(F.data.startswith("admin_unban_user:"))
async def callback_unban_user(query: types.CallbackQuery):
    if await _deny(query):
        return
    target_id = int(query.data.split(":", 1)[1])
    user_language = await _get_user_language(query.from_user.id)
    await user_mod.db.unban_user(target_id)
    await query.answer(get_text("saved", user_language), show_alert=True)
    await query.message.edit_reply_markup(
        reply_markup=user_profile_keyboard(target_id, False, user_language)
    )
    logging.event("user_unbanned", admin_id=query.from_user.id, target_id=target_id)


@router.callback_query(F.data == "admin_banned_users")
async def callback_banned_users(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    users = await user_mod.db.get_banned_users()

    if not users:
        await query.message.edit_text(
            "Bloklangan foydalanuvchilar yo'q." if user_language == "uz" else "No banned users.",
            reply_markup=return_to_admin_main_keyboard(user_language),
        )
        await query.answer()
        return

    await query.message.edit_text(
        "<b>🚫 Bloklangan foydalanuvchilar</b>" if user_language == "uz" else "<b>🚫 Banned Users</b>",
        reply_markup=banned_users_keyboard(users, user_language),
        parse_mode="HTML",
    )
    await query.answer()


# ---------------------------------------------------------------------------
# Bot settings (aggregated view)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_bot_settings")
async def callback_bot_settings_menu(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    bot_enabled = await user_mod.db.is_bot_enabled()

    await query.message.edit_text(
        "<b>⚙️ Bot sozlamalari</b>" if user_language == "uz" else "<b>⚙️ Bot Settings</b>",
        reply_markup=bot_settings_keyboard(user_language, bot_enabled=bot_enabled),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "admin_toggle_bot_enabled")
async def callback_toggle_bot_enabled(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    currently_enabled = await user_mod.db.is_bot_enabled()

    if currently_enabled:
        # Ask for confirmation before disabling the whole bot.
        await query.message.edit_text(
            "⚠️ Botni o'chirmoqchimisiz? Bu barcha foydalanuvchilar uchun botni to'xtatadi."
            if user_language == "uz"
            else "⚠️ Disable the bot for all users?",
            reply_markup=bot_disable_confirm_keyboard(user_language),
        )
        await query.answer()
        return

    await user_mod.db.set_bot_enabled(True)
    await query.answer("✅ " + ("Bot yoqildi" if user_language == "uz" else "Bot enabled"), show_alert=True)
    await query.message.edit_text(
        "<b>⚙️ Bot sozlamalari</b>" if user_language == "uz" else "<b>⚙️ Bot Settings</b>",
        reply_markup=bot_settings_keyboard(user_language, bot_enabled=True),
        parse_mode="HTML",
    )
    logging.event("bot_enabled_toggled", admin_id=query.from_user.id, enabled=True)


@router.callback_query(F.data == "admin_bot_disable_confirm")
async def callback_bot_disable_confirm(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    await user_mod.db.set_bot_enabled(False)
    await query.answer("🔴 " + ("Bot o'chirildi" if user_language == "uz" else "Bot disabled"), show_alert=True)
    await query.message.edit_text(
        "<b>⚙️ Bot sozlamalari</b>" if user_language == "uz" else "<b>⚙️ Bot Settings</b>",
        reply_markup=bot_settings_keyboard(user_language, bot_enabled=False),
        parse_mode="HTML",
    )
    logging.event("bot_enabled_toggled", admin_id=query.from_user.id, enabled=False)


# ---------------------------------------------------------------------------
# Logs & errors
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_logs")
async def callback_logs_menu(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    await query.message.edit_text(
        "<b>📝 Loglar va xatolar</b>" if user_language == "uz" else "<b>📝 Logs & Errors</b>",
        reply_markup=logs_management_keyboard(user_language),
        parse_mode="HTML",
    )
    await query.answer()


# ---------------------------------------------------------------------------
# Bot control
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin_bot_control")
async def callback_bot_control_menu(query: types.CallbackQuery):
    if await _deny(query):
        return
    user_language = await _get_user_language(query.from_user.id)
    bot_enabled = await user_mod.db.is_bot_enabled()
    await query.message.edit_text(
        "<b>🔄 Botni boshqarish</b>" if user_language == "uz" else "<b>🔄 Bot Control</b>",
        reply_markup=bot_control_keyboard(user_language, bot_enabled),
        parse_mode="HTML",
    )
    await query.answer()
