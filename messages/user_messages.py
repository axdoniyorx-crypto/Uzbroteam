def cancel():
    return "✖️ Bekor qilish"


def default_welcome_message():
    return (
        "╭━━━ ✦ <b>BirBosBot</b> ✦ ━━━╮\n\n"
        "❤️ <b>Xush kelibsiz!</b>\n\n"
        "🔗 Havolani yuboring — video, rasm yoki audio bo'lsin, "
        "barchasini tez va oson yuklab olasiz. ⚡\n\n"
        "╰━━━━━━━━━━━━━━━━╯\n\n"
        "🌐 <b>Qo'llab-quvvatlanadigan platformalar</b>\n"
        "📷 Instagram &#8226; 🎵 TikTok\n"
        "▶️ YouTube &#8226; 🧵 Threads\n"
        "🐦 X / Twitter &#8226; 🎧 SoundCloud\n"
        "🟢 Spotify &#8226; 📌 Pinterest\n\n"
        "⚡ Tezlik &#8226; 🎯 Sifat &#8226; 😊 Qulaylik\n\n"
        "👇 Quyidagi menyudan foydalaning"
    )


def default_welcome_message_en():
    return (
        "╭━━━ ✦ <b>BirBosBot</b> ✦ ━━━╮\n\n"
        "❤️ <b>Welcome!</b>\n\n"
        "🔗 Send a link — video, photo, or audio — "
        "and download it instantly. ⚡\n\n"
        "╰━━━━━━━━━━━━━━━━╯\n\n"
        "🌐 <b>Supported platforms</b>\n"
        "📷 Instagram &#8226; 🎵 TikTok\n"
        "▶️ YouTube &#8226; 🧵 Threads\n"
        "🐦 X / Twitter &#8226; 🎧 SoundCloud\n"
        "🟢 Spotify &#8226; 📌 Pinterest\n\n"
        "⚡ Speed &#8226; 🎯 Quality &#8226; 😊 Simplicity\n\n"
        "👇 Use the menu below"
    )


async def welcome_message(language: str | None = None):
    """Returns the /start greeting text.

    If the admin has configured a custom greeting via the admin panel,
    that text is returned instead of the built-in default (regardless of
    language — a custom message is admin-authored and shown as-is).
    """
    try:
        from app_context import db as _db
        custom = await _db.get_welcome_message()
        if custom:
            return custom
    except Exception:
        pass
    if (language or "uz").lower().startswith("en"):
        return default_welcome_message_en()
    return default_welcome_message()


def settings():
    return (
        "<b>⚙️ Sozlamalar</b>\n"
        "Yuklamalar qanday yuborilishini shu tugmalar orqali moslang. "
        "O'zgarishlar faqat sizning hisobingizga tegishli bo'ladi."
    )


def settings_private_only():
    return (
        "Sozlamalar faqat shaxsiy chatda mavjud. Sozlamalarni o'zgartirish uchun botga DM oching."
    )


def get_field_text(field: str):
    texts = {
        "captions": (
            "<b>📝 Tavsiflar</b>\n"
            "Yuklab olingan mediada post tavsiflarini ko'rsatish yoki yashirish. "
            "Ba'zi manbalar tavsif taqdim etmasligi mumkin."
        ),
        "delete_message": (
            "<b>🗑️ Xabarlarni o'chirish</b>\n"
            "Yuklab olish tugagach, sizning havolangizni avtomatik o'chirish."
        ),
        "info_buttons": (
            "<b>ℹ️ Ma'lumot tugmalari</b>\n"
            "Yuklab olingan media ostidagi qo'shimcha ma'lumot tugmalarini yoqish/o'chirish."
        ),
        "url_button": (
            "<b>🔗 URL tugmasi</b>\n"
            "Asl post havolasi bilan tugmani ko'rsatish yoki yashirish."
        ),
        "audio_button": (
            "<b>🎧 MP3 tugmasi</b>\n"
            "Audio mavjud bo'lganda 'MP3 yuklab olish' tugmasini yoqish/o'chirish."
        ),
        "file_button": (
            "<b>📄 Fayl tugmasi</b>\n"
            "Video ostida 'Faylni yuklab olish' tugmasini ko'rsatish yoki yashirish — talab bo'yicha asl, siqilmagan faylni olish uchun."
        ),
        "video_quality": (
            "<b>🎬 Video sifati</b>\n"
            "Video yuklab olish uchun afzal ko'rgan sifatni tanlang:\n\n"
            "• <b>Eng yaxshi (1080p+)</b>: Maksimal mumkin bo'lgan sifat.\n"
            "• <b>Muvozanatli (720p)</b>: Sifat va tezlikning yaxshi muvozanati.\n"
            "• <b>Trafik tejash (480p)</b>: Tezroq yuklab olish, minimal trafik sarfi."
        ),
        "as_document": (
            "<b>📄 Fayl sifatida yuborish</b>\n"
            "Yoqilganda, video va rasmlar 100% asl sifatini saqlagan holda siqilmagan fayl (.mp4 / .jpg) sifatida yuboriladi."
        ),
        "audio_format": (
            "<b>🎵 Audio format</b>\n"
            "Musiqa yuklab olish uchun standart audio formatni tanlang:\n\n"
            "• <b>MP3</b>: Standart universal audio format.\n"
            "• <b>M4A (AAC)</b>: iOS va Mac uchun yuqori sifatli, ixcham format.\n"
            "• <b>FLAC / Original</b>: Mavjud bo'lganda siqilmagan, yo'qotishsiz audio."
        ),
    }
    return texts.get(field, "<b>Sozlamalar</b>\nBu variant uchun tavsif hali mavjud emas.")


def captions(user_captions, post_caption, bot_url, *, limit: int = 1024):
    import html

    def _truncate_escaped(value: str, max_len: int) -> str:
        if max_len <= 0:
            return ""
        if len(value) <= max_len:
            return value
        cut = value[:max_len]
        amp = cut.rfind("&")
        semi = cut.rfind(";")
        if amp > semi:
            cut = cut[:amp]
        return cut

    footer = '<tg-emoji emoji-id="5283080528818360566">🚀</tg-emoji> <a href="{bot_url}">@birbosbot</a> orqali yuborildi'.format(bot_url=bot_url)

    if user_captions == "on" and post_caption:
        body = html.escape(str(post_caption))
        sep = "\n\n"
        # Keep footer intact; only shrink the body.
        budget = limit - len(sep) - len(footer)
        if budget <= 0:
            return _truncate_escaped(footer, limit)

        if len(body) > budget:
            suffix = "…"
            body = _truncate_escaped(body, max(0, budget - len(suffix))).rstrip() + suffix

        return f"{body}{sep}{footer}"

    return _truncate_escaped(footer, limit)


def downloading_audio_status():
    return "🎧 Audio yuklab olinmoqda..."


def downloading_video_status():
    return "<tg-emoji emoji-id='5375464961822695044'>🎬</tg-emoji> Video yuklab olinmoqda..."



def uploading_status():
    return "☁️ Fayl Telegram'ga yuklanmoqda..."


def retrying_again_status(next_attempt: int, total_attempts: int):
    return f"Xatolik, qayta urinilmoqda... ({next_attempt}/{total_attempts})"


def dm_start_required():
    return "<tg-emoji emoji-id='5472308992514464048'>🔒</tg-emoji> Birinchi marta sozlash kerak: DM oching, Start tugmasini bosing va havolani qayta yuboring."


def duplicate_link_processing():
    return "Bu havola allaqachon qayta ishlanmoqda. Bir necha soniya kuting."


def duplicate_link_recently_processed():
    return "Bu havola yaqinda qayta ishlangan edi. Agar hali kerak bo'lsa, bir necha soniyadan keyin qayta urinib ko'ring."


def settings_admin_only():
    return "Guruh chatlarida /settings buyrug'ini faqat guruh administratorlari ochishi mumkin."


def invalid_settings_option():
    return "Noto'g'ri sozlama varianti."


def join_group(chat_title: str) -> str:
    return (
        "╭━━━ ✦ <b>BirBosBot</b> ✦ ━━━╮\n\n"
        "✦ <b>{chat_title}</b> guruhiga qo'shganingiz uchun rahmat! 🌸\n\n"
        "╰─➤ To'liq funksionallikni ochish uchun menga "
        "<b>administrator huquqlarini</b> bering 🔓\n\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "✦ <b>BirBosBot</b> ✦\n"
        "Thanks for adding me to <b>{chat_title}</b>! 🌸\n"
        "Please grant me <b>administrator rights</b> to unlock full "
        "functionality 🔓"
    ).format(chat_title=chat_title)


def admin_rights_granted(chat_title: str) -> str:
    return (
        "╭━━━ ✦ <b>BirBosBot</b> ✦ ━━━╮\n\n"
        "✦ <b>{chat_title}</b> guruhida administrator huquqlarini "
        "berganingiz uchun rahmat! 🌸\n\n"
        "╰─➤ Yuklab olishlarning muammosiz ishlashini ta'minlashga "
        "tayyorman 💻\n\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "✦ <b>BirBosBot</b> ✦\n"
        "Thanks for granting admin rights in <b>{chat_title}</b>! 🌸\n"
        "I'm ready to keep downloads running smoothly 💻"
    ).format(chat_title=chat_title)


def keyboard_removed():
    return "Klaviatura olib tashlandi."


def tiktok_live_not_supported():
    return "TikTok LIVE translyatsiyalari hozircha qo'llab-quvvatlanmaydi. Oddiy TikTok post havolasini yuboring."


def delete_permission_warning():
    return "Avtomatik o'chirish amalga oshmadi: bu chatda xabarlarni o'chirish uchun ruxsat yo'q. Iltimos, o'chirish huquqini bering yoki sozlamalarda avtomatik o'chirishni o'chiring."


def stats_temporarily_unavailable():
    return "Hozircha statistikani hosil qilib bo'lmadi. Birozdan keyin qayta urinib ko'ring."


def no_queue_metrics_yet():
    return "Navbat statistikasi hali mavjud emas."


def open_bot_for_audio():
    return "Audio yuklab olish uchun botni shaxsiy chatda oching."


def audio_fetch_failed():
    return "Audio ma'lumotini olib bo'lmadi. Birozdan keyin qayta urinib ko'ring."


def audio_download_failed():
    return "Audio yuklab olinmadi. Birozdan keyin qayta urinib ko'ring."


def spotify_metadata_failed():
    return "Bu Spotify trekini o'qib bo'lmadi. Havolani tekshirib, qayta urinib ko'ring."


def spotify_source_not_found():
    return "Bu Spotify treki uchun mos audio manba topilmadi."


def inline_album_link_invalid():
    return "Bu albom havolasi eskirgan yoki noto'g'ri."


def inline_photo_title(service_name: str):
    return f"{service_name} rasmi"


def inline_photo_description():
    return "Bitta rasm"


def inline_album_title(service_name: str):
    return f"{service_name} albomi"


def inline_album_description():
    return "To'liq albomni botda ochish"


def inline_open_full_album_button():
    return "To'liq albomni ochish"


def inline_photos_title(service_name: str):
    return f"{service_name} rasmlari"


def inline_photos_not_supported(service_name: str):
    return f"{service_name} rasmlari inline rejimda qo'llab-quvvatlanmaydi."


def inline_send_video_button():
    return "Videoni inline yuborish"


def inline_send_video_prompt(service_name: str):
    return f"{service_name} videosi tayyorlanmoqda...\nAgar avtomatik boshlanmasa, pastdagi tugmani bosing."


def inline_send_audio_prompt(service_name: str):
    return f"{service_name} audiosi tayyorlanmoqda...\nAgar avtomatik boshlanmasa, pastdagi tugmani bosing."


def inline_video_already_processing():
    return "Bu inline video allaqachon tayyorlanmoqda."


def inline_video_already_sent():
    return "Bu inline video allaqachon yuborilgan."


def supported_sites_message(bot_username: str | None = None):
    return help_message(bot_username)


def category_settings_text(category: str) -> str:
    if category == "media":
        return (
            "<b>🎬 Media va sifat sozlamalari</b>\n\n"
            "Video sifati, fayl formati va audio variantlarini sozlang:"
        )
    if category == "appearance":
        return (
            "<b>🎨 Ko'rinish va tugmalar</b>\n\n"
            "Post tavsiflari, asl URL havolalari va amal tugmalarini moslang:"
        )
    if category == "chat":
        return (
            "<b>💬 Chat va tozalash</b>\n\n"
            "Guruh chati xatti-harakati va xabarlarni tozalash sozlamalarini boshqaring:"
        )
    return settings()


def help_message(bot_username: str | None = None, language: str | None = None) -> str:
    username = bot_username or "birbosbot"
    if (language or "uz").lower().startswith("en"):
        return (
            "╭━━━ ✦ <b>BirBosBot</b> ✦ ━━━╮\n"
            "❓ <b>Help &amp; guide</b>\n"
            "╰━━━━━━━━━━━━━━━━╯\n\n"
            "Send one link, or drop several in a single message — I'll detect and deliver the media automatically.\n\n"
            "<blockquote expandable><b>📷 Instagram &amp; Threads</b>\n"
            "• Posts, Reels, IGTV, and Stories\n"
            "• Photo carousels and multi-media albums\n"
            "• Copy the link via Share → Copy link</blockquote>\n\n"
            "<blockquote expandable><b>🎵 TikTok</b>\n"
            "• Watermark-free video downloads\n"
            "• Photo carousels and slideshows\n"
            "• MP3 audio extraction supported</blockquote>\n\n"
            "<blockquote expandable><b>▶️ YouTube &amp; YouTube Music</b>\n"
            "• YouTube Shorts and regular videos\n"
            "• High-quality audio and video streams\n"
            "• Tap the MP3 button for audio</blockquote>\n\n"
            "<blockquote expandable><b>🐦 X / Twitter &amp; 📌 Pinterest</b>\n"
            "• X / Twitter videos, GIFs, and photos\n"
            "• Pinterest video and photo Pins</blockquote>\n\n"
            "<blockquote expandable><b>🎧 SoundCloud &amp; 🟢 Spotify</b>\n"
            "• High-quality SoundCloud audio tracks\n"
            "• Spotify track matching and audio download</blockquote>\n\n"
            f"<blockquote expandable><b>⚡ Inline mode</b>\n"
            f"• Type <code>@{username} [link]</code> in any chat\n"
            "• Quick preview and direct media sharing</blockquote>\n\n"
            "<blockquote expandable><b>📦 Batch downloads</b>\n"
            "• Drop up to 6 links in one message\n"
            "• They're delivered one by one to keep the chat tidy</blockquote>"
        )
    return (
        "╭━━━ ✦ <b>BirBosBot</b> ✦ ━━━╮\n"
        "❓ <b>Yordam va qo'llanma</b>\n"
        "╰━━━━━━━━━━━━━━━━╯\n\n"
        "Bitta havola yuboring yoki bitta xabarda bir nechta havola joylashtiring. Bot mediani avtomatik ravishda ajratib, sizga yetkazadi.\n\n"
        "<blockquote expandable><b>📷 Instagram va Threads</b>\n"
        "• Post, Reels, IGTV va Stories yuklab olish\n"
        "• Rasm karusellari va ko'p-mediali albomlar\n"
        "• Havolani Share → Copy link orqali nusxalang</blockquote>\n\n"
        "<blockquote expandable><b>🎵 TikTok</b>\n"
        "• Suv belgisisiz video yuklab olish\n"
        "• Rasm karusellari va slaydshoular\n"
        "• MP3 audio ajratib olish qo'llab-quvvatlanadi</blockquote>\n\n"
        "<blockquote expandable><b>▶️ YouTube va YouTube Music</b>\n"
        "• YouTube Shorts va oddiy videolar\n"
        "• Yuqori sifatli audio va video oqimlar\n"
        "• Audio yuklab olish uchun MP3 tugmasini bosing</blockquote>\n\n"
        "<blockquote expandable><b>🐦 X / Twitter va 📌 Pinterest</b>\n"
        "• X / Twitter videolari, GIF va rasmlar\n"
        "• Pinterest video va rasm Pinlari</blockquote>\n\n"
        "<blockquote expandable><b>🎧 SoundCloud va 🟢 Spotify</b>\n"
        "• Yuqori sifatli SoundCloud audio treklari\n"
        "• Spotify trek moslashtirish va audio yuklab olish</blockquote>\n\n"
        f"<blockquote expandable><b>⚡ Inline rejim</b>\n"
        f"• Istalgan chatda <code>@{username} [havola]</code> deb yozing\n"
        "• Tezkor ko'rish va to'g'ridan-to'g'ri media ulashish</blockquote>\n\n"
        "<blockquote expandable><b>📦 Ommaviy yuklab olish</b>\n"
        "• Bitta xabarda 6 tagacha havola joylashtiring\n"
        "• Chatni toza saqlash uchun birma-bir yetkaziladi</blockquote>"
    )


def referral_message(bot_username: str, user_id: int, invited_count: int) -> str:
    username = bot_username or "birbosbot"
    ref_link = f"https://t.me/{username}?start=ref_{user_id}"
    return (
        "<b>👥 Sizning taklif dasturingiz</b>\n\n"
        "Do'stlaringizni @birbosbot'dan foydalanishga taklif qiling! Shaxsiy taklif havolangizni ulashing:\n"
        f"<code>{ref_link}</code>\n\n"
        f"Taklif qilingan foydalanuvchilar: <b>{invited_count}</b>"
    )


def batch_links_started(processed_total: int, detected_total: int | None = None):
    if detected_total is not None and detected_total > processed_total:
        return (
            f"{detected_total} ta qo'llab-quvvatlanadigan havola topildi. "
            f"Chat tartibli bo'lishi uchun birinchi {processed_total} tasini birma-bir qayta ishlayman."
        )
    return f"{processed_total} ta qo'llab-quvvatlanadigan havola topildi. Chat tartibli bo'lishi uchun ularni birma-bir qayta ishlayman."


def batch_link_progress(current: int, total: int, service_name: str):
    return f"{current}/{total} havola qayta ishlanmoqda: {service_name}..."


def batch_links_finished(total: int):
    return f"{total} ta havola uchun ommaviy qayta ishlash yakunlandi."


def timeout_error():
    return "So'rov vaqti tugadi. Manba hozir sekin ishlayotgan bo'lishi mumkin. Birozdan keyin qayta urinib ko'ring."


def something_went_wrong():
    return (
        "Bu havolani hozir qayta ishlab bo'lmadi.\n"
        "U shaxsiy, o'chirilgan, hudud bo'yicha cheklangan yoki manba tomonidan vaqtincha bloklangan bo'lishi mumkin. "
        "Birozdan keyin qayta urinib ko'ring."
    )


def video_too_large():
    return "Video Telegram uchun juda katta. Qisqaroq video yoki mavjud bo'lsa MP3/audio variantini sinab ko'ring."


def audio_too_large():
    return "Audio Telegram uchun juda katta. Qisqaroq trek yoki boshqa manba havolasini sinab ko'ring."


def nothing_found():
    return "Media topilmadi. Havola ochiq (public), muddati o'tmagan va to'g'ridan-to'g'ri post yoki videoga ishora qilishini tekshiring."


def audio_button_expired():
    return "Bu tugma muddati o'tgan. Videoni qaytadan yuboring va MP3 tugmasini qayta bosing."


def music_search_started(query: str) -> str:
    return f"🔍 <b>{query}</b>\n\nQidirilmoqda, biroz kuting..."


def music_search_no_results(query: str) -> str:
    return f"«{query}» bo'yicha hech narsa topilmadi. Boshqa nom bilan urinib ko'ring."


def music_search_results(query: str, results: list[dict]) -> str:
    lines = [f"🔍 <b>{query}</b>\n"]
    for index, item in enumerate(results, start=1):
        title = item.get("title") or "Noma'lum"
        uploader = item.get("uploader")
        duration = item.get("duration")
        duration_text = ""
        if isinstance(duration, (int, float)) and duration > 0:
            minutes, seconds = divmod(int(duration), 60)
            duration_text = f" — {minutes}:{seconds:02d}"
        author_text = f" ({uploader})" if uploader else ""
        lines.append(f"<b>{index}.</b> {title}{author_text}{duration_text}")
    return "\n".join(lines)


def music_search_expired() -> str:
    return "Bu qidiruv natijalari eskirgan. Qo'shiq nomini qaytadan yuboring."


def music_search_invalid_choice() -> str:
    return "Noto'g'ri tanlov."


def shazam_recognizing_status() -> str:
    return "🎧 Qo'shiq aniqlanmoqda, biroz kuting..."


def shazam_no_match() -> str:
    return "😔 Qo'shiq aniqlanmadi. Ovoz tiniqroq va uzunroq bo'lgan qism bilan qayta urinib ko'ring."


def shazam_file_too_large() -> str:
    return (
        "Fayl hajmi juda katta. Telegram ovozli/video xabarlarni faqat 20MB "
        "gacha yuklab olishga ruxsat beradi — qisqaroq parcha yuboring."
    )


def shazam_match_found(track: dict) -> str:
    title = track.get("title") or "Noma'lum"
    artist = track.get("artist") or ""
    lines = ["🎧 <b>Topildi!</b>\n", f"<b>{title}</b>"]
    if artist:
        lines.append(artist)
    genre = track.get("genre")
    if genre:
        lines.append(f"\n🎵 {genre}")
    links = []
    if track.get("apple_music_url"):
        links.append(f"<a href=\"{track['apple_music_url']}\">Apple Music</a>")
    if track.get("spotify_url"):
        links.append(f"<a href=\"{track['spotify_url']}\">Spotify</a>")
    if links:
        lines.append("\n" + " • ".join(links))
    lines.append("\n👇 To'liq qo'shiqni yuklab olish uchun tugmani bosing")
    return "\n".join(lines)
