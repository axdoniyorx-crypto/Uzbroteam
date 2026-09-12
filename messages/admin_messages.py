def admin_panel(
    *args,
    total_count=None,
    private_count=None,
    group_count=None,
    active_user_count=None,
    inactive_user_count=None,
    dm_total=None,
    dm_active=None,
    dm_inactive=None,
    dm_banned=None,
    groups_total=None,
    groups_active=None,
    groups_inactive=None,
    total_reach=None,
    tracked_group_members=None,
    **kwargs,
):
    if len(args) == 1 and isinstance(args[0], dict):
        d = args[0]
        dm_total = d.get("dm_total", dm_total)
        dm_active = d.get("dm_active", dm_active)
        dm_inactive = d.get("dm_inactive", dm_inactive)
        dm_banned = d.get("dm_banned", dm_banned)
        groups_total = d.get("groups_total", groups_total)
        groups_active = d.get("groups_active", groups_active)
        groups_inactive = d.get("groups_inactive", groups_inactive)
        total_reach = d.get("total_reach", total_reach)
        tracked_group_members = d.get("tracked_group_members", tracked_group_members)
        total_count = d.get("user_count", total_count)
        private_count = d.get("private_chat_count", private_count)
        group_count = d.get("group_chat_count", group_count)
        active_user_count = d.get("active_user_count", active_user_count)
        inactive_user_count = d.get("inactive_user_count", inactive_user_count)
    elif len(args) == 9:
        (
            dm_total,
            dm_active,
            dm_inactive,
            dm_banned,
            groups_total,
            groups_active,
            groups_inactive,
            total_reach,
            tracked_group_members,
        ) = args
    elif len(args) == 5:
        (
            total_count,
            private_count,
            group_count,
            active_user_count,
            inactive_user_count,
        ) = args

    if dm_total is not None:
        reach_val = total_reach or 0
        return (
            "<b>Salom, bu — admin panel.</b>\n\n"
            "👤 <b>Shaxsiy chatlar (DM):</b>\n"
            f"  ├ DM bilan jami: <b>{dm_total}</b>\n"
            f"  ├ ✅ Faol (yetib boriladi): <b>{dm_active or 0}</b>\n"
            f"  ├ 🚫 Nofaol (botni bloklagan): <b>{dm_inactive or 0}</b>\n"
            f"  └ ⛔ Bloklangan: <b>{dm_banned or 0}</b>\n\n"
            "🏘 <b>Guruhlar:</b>\n"
            f"  ├ Guruhlar jami: <b>{groups_total or 0}</b>\n"
            f"  ├ ✅ Faol (bot a'zo): <b>{groups_active or 0}</b>\n"
            f"  ├ 🚫 Nofaol (chetlatilgan/chiqib ketgan): <b>{groups_inactive or 0}</b>\n"
            f"  ├ 👥 <b>Taxminiy qamrov:</b> <b>~{reach_val:,} a'zo</b>\n"
            f"  └ 💬 Kuzatilgan yozuvchilar: <b>{tracked_group_members or 0}</b>"
        )

    return ("""<b>Salom, bu — admin panel.</b>

👥 Jami chatlar: <b>{total_count}</b>
👤 Shaxsiy foydalanuvchilar: <b>{private_count}</b>
🏘 Guruhlar: <b>{group_count}</b>

✅ Faol: <b>{active_user_count}</b>
🚫 Nofaol: <b>{inactive_user_count}</b>""").format(
        total_count=total_count,
        private_count=private_count,
        group_count=group_count,
        active_user_count=active_user_count,
        inactive_user_count=inactive_user_count,
    )


def not_groups():
    return "Bu buyruqni guruhda ishlatib bo'lmaydi!"


def finish_mailing(
    total: int = 0,
    delivered: int = 0,
    unreachable: int = 0,
    migrated: int = 0,
    failed: int = 0,
) -> str:
    if total <= 0 and delivered <= 0:
        return "Xabar tarqatish yakunlandi!"
    return (
        f"<b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"📊 <b>Yetkazish hisoboti:</b>\n"
        f"├ 🎯 Jami maqsad: <b>{total}</b>\n"
        f"├ ✅ Yetkazildi: <b>{delivered}</b>\n"
        f"├ 🚫 Yetib bo'lmadi / Bloklangan: <b>{unreachable}</b>\n"
        f"├ 🔄 Supergruppaga ko'chirilgan: <b>{migrated}</b>\n"
        f"└ ⚠️ Muvaffaqiyatsiz: <b>{failed}</b>"
    )


def start_mailing():
    return "Xabar tarqatish boshlanmoqda..."


def mailing_audience_preview(total_users, active_users, inactive_users, banned_users, private_users, group_users):
    return ("""<b>Xabar tarqatish auditoriyasi ko'rinishi</b>
Qayta ishlanadigan foydalanuvchilar: <b>{total_users}</b>
Faol: <b>{active_users}</b>
Nofaol: <b>{inactive_users}</b>
Bloklangan: <b>{banned_users}</b>
Shaxsiy chatlar: <b>{private_users}</b>
Guruhlar: <b>{group_users}</b>

Yuborish uchun xabarni kiriting:""").format(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        banned_users=banned_users,
        private_users=private_users,
        group_users=group_users,
    )


def mailing_select_audience() -> str:
    return (
        "<b>Ommaviy xabar tarqatish</b>\n\n"
        "Tarqatish uchun maqsadli auditoriyani tanlang:"
    )


def mailing_audience_preview_segmented(
    audience_type: str | None = None,
    total_recipients: int = 0,
    active_count: int = 0,
    inactive_count: int = 0,
    estimated_reach: int = 0,
    *,
    audience_name: str | None = None,
    **kwargs,
) -> str:
    chosen_audience = audience_name if audience_name is not None else (audience_type or "")
    lines = [
        "<b>Xabar tarqatish auditoriyasi ko'rinishi</b>",
        f"Maqsadli auditoriya: <b>{chosen_audience}</b>",
        f"Qayta ishlanadigan qabul qiluvchilar: <b>{total_recipients}</b>",
    ]
    if active_count > 0 or inactive_count > 0:
        lines.append(f"Faol: <b>{active_count}</b>")
        if inactive_count > 0:
            lines.append(f"Nofaol: <b>{inactive_count}</b>")
    if estimated_reach > 0:
        lines.append(f"Taxminiy qamrov: <b>~{estimated_reach:,} a'zo</b>")
    lines.extend([
        "",
        "Yuborish uchun xabarni kiriting:",
    ])
    return "\n".join(lines)


def canceled():
    return "Amal bekor qilindi!"


def your_message_sent():
    return "Xabaringiz yuborildi!"


def something_went_wrong():
    return "Nimadir xato ketdi, batafsil ma'lumot uchun logni ko'ring!"


def please_type_message():
    return "Iltimos, xabar matnini yozing:"


def log_deleted():
    return "Log o'chirildi, yangisini yozishni boshlayapman."


def active_users_check_started(total_users):
    return f"{total_users} ta foydalanuvchi uchun mavjudlik tekshiruvi boshlandi..."


def active_users_check_completed(total_users, reachable_users, unreachable_users):
    return ("""<b>Mavjudlik tekshiruvi yakunlandi.</b>
Qayta ishlangan foydalanuvchilar: <b>{total_users}</b>
Yetib boriladi: <b>{reachable_users}</b>
Yetib bo'lmaydi: <b>{unreachable_users}</b>""").format(
        total_users=total_users,
        reachable_users=reachable_users,
        unreachable_users=unreachable_users,
    )


def active_users_check_no_targets():
    return "Tekshirish uchun mavjud foydalanuvchilar yo'q."


def check_groups_started(total_groups: int) -> str:
    return f"{total_groups} ta guruh uchun mavjudlik va qamrov tekshiruvi boshlandi..."


def check_groups_completed(
    total_groups: int,
    reachable_groups: int = 0,
    unreachable_groups: int = 0,
    total_reach: int = 0,
    *,
    active_groups: int | None = None,
    kicked_groups: int | None = None,
) -> str:
    reachable = active_groups if active_groups is not None else reachable_groups
    unreachable = kicked_groups if kicked_groups is not None else unreachable_groups
    reach_val = total_reach or 0
    return (
        "<b>Guruh tekshiruvi yakunlandi.</b>\n\n"
        f"Qayta ishlangan guruhlar: <b>{total_groups}</b>\n"
        f"Yetib boriladi (bot a'zo): <b>{reachable}</b>\n"
        f"Yetib bo'lmaydi (chetlatilgan/chiqib ketgan): <b>{unreachable}</b>\n"
        f"Jami taxminiy qamrov: <b>~{reach_val:,} a'zo</b>"
    )


def check_groups_no_targets() -> str:
    return "Tekshirish uchun faol guruhlar yo'q."


active_groups_check_started = check_groups_started
active_groups_check_completed = check_groups_completed
active_groups_check_no_targets = check_groups_no_targets


def enter_chat_id():
    return "Chat ID'sini kiriting (masalan, -1001234567890):"


def invalid_chat_id():
    return "Chat ID -1001234567890 kabi raqam bo'lishi kerak. Qayta urinib ko'ring yoki Bekor qilishni bosing."


def enter_chat_message():
    return "Ushbu chatga yubormoqchi bo'lgan xabarni kiriting:"


def known_chat_target(chat_id, chat_name, chat_username, status):
    return ("""<b>Ma'lum chat nishoni</b>
ID: <b>{chat_id}</b>
Nomi: <b>{chat_name}</b>
Foydalanuvchi nomi: <b>{chat_username}</b>
Holati: <b>{status}</b>""").format(
        chat_id=chat_id,
        chat_name=chat_name,
        chat_username=chat_username or "—",
        status=status or "noma'lum",
    )


def unknown_chat_target(chat_id):
    return (
        "{chat_id} chati hali lokal bazada yo'q. "
        "Bot kirish huquqiga ega bo'lsa, baribir xabarni yuborishga harakat qilaman."
    ).format(chat_id=chat_id)


def chat_message_sent(chat_id):
    return f"Xabar {chat_id} chatiga yetkazildi."


def chat_message_failed(chat_id):
    return f"{chat_id} chatiga xabar yuborilmadi. Botning shu yerda a'zo va yoza olishiga ishonch hosil qiling."


def chat_message_sending():
    return "Xabar yuborilmoqda..."


def downloads_cleanup_blocked(active_jobs, queued_jobs):
    return (
        "Yuklamalar hali ishlayotgani sababli tozalash o'tkazib yuborildi. "
        "faol_vazifalar={active_jobs}, navbatdagi_vazifalar={queued_jobs}."
    ).format(active_jobs=active_jobs, queued_jobs=queued_jobs)


def downloads_cleanup_finished(removed_files, removed_dirs, skipped_recent_files):
    return (
        "Yuklamalarni tozalash yakunlandi. {removed_files} ta fayl va {removed_dirs} ta papka o'chirildi; "
        "{skipped_recent_files} ta yaqinda yuklangan fayl o'tkazib yuborildi."
    ).format(
        removed_files=removed_files,
        removed_dirs=removed_dirs,
        skipped_recent_files=skipped_recent_files,
    )


def welcome_message_settings_menu(current_text: str, is_custom: bool) -> str:
    status = "✏️ Maxsus (admin tomonidan sozlangan)" if is_custom else "⚙️ Standart (dastur bilan birga keladi)"
    return (
        "<b>👋 Salomlashish xabari</b>\n"
        f"Holati: {status}\n\n"
        "Hozirgi xabar quyida ko'rsatilgan. Foydalanuvchi /start bosganda aynan shu xabar yuboriladi.\n"
        "Matn ichida HTML teglaridan (masalan &lt;b&gt;, &lt;i&gt;) foydalanishingiz mumkin.\n\n"
        "———————————————\n"
        f"{current_text}\n"
        "———————————————"
    )


def welcome_message_prompt() -> str:
    return (
        "Yangi salomlashish xabarini yuboring.\n\n"
        "• HTML teglardan foydalanishingiz mumkin (&lt;b&gt;, &lt;i&gt;, &lt;a href=...&gt; va h.k.).\n"
        "• Bekor qilish uchun pastdagi tugmani bosing."
    )


def welcome_message_updated() -> str:
    return "✅ Salomlashish xabari yangilandi. Endi /start bosganda foydalanuvchilar shu matnni ko'radi."


def welcome_message_reset() -> str:
    return "♻️ Salomlashish xabari standart holatiga qaytarildi."


def welcome_message_invalid() -> str:
    return "Xabar matni bo'sh bo'lishi mumkin emas. Iltimos, matn yuboring."


def welcome_message_too_long(limit: int) -> str:
    return f"Xabar juda uzun. Iltimos, {limit} belgidan qisqaroq matn yuboring."
