# English language messages

MESSAGES = {
    # Commands
    "start_command": "Start",
    "help_command": "Help",
    "settings_command": "Settings",
    "stats_command": "Statistics",
    "admin_command": "Admin",

    # Language choice
    "choose_language": "Choose language / Tilni tanlang:",
    "language_uzbek": "🇺🇿 O'zbek",
    "language_english": "🇬🇧 English",

    # Welcome
    "welcome": (
        '<b>Welcome to BirBosBot <tg-emoji emoji-id="5420141555233071341">❤️</tg-emoji></b>\n\n'
        "Send one link, or paste several links in one message, and I'll download what I can.\n\n"
        "<b>Supported sites</b>\n"
        '<tg-emoji emoji-id="5233671414023753035">📷</tg-emoji> Instagram\n'
        '<tg-emoji emoji-id="5370693953236539466">🧵</tg-emoji> Threads\n'
        '<tg-emoji emoji-id="5233597424622144804">🎵</tg-emoji> TikTok\n'
        '<tg-emoji emoji-id="5233311027612913110">▶️</tg-emoji> YouTube\n'
        '<tg-emoji emoji-id="5231309843435919433">🐦</tg-emoji> X / Twitter\n'
        '<tg-emoji emoji-id="5233448977667492819">🎧</tg-emoji> SoundCloud\n'
        '<tg-emoji emoji-id="5391001065418172193">🟢</tg-emoji> Spotify\n'
        '<tg-emoji emoji-id="5233210422298974231">📌</tg-emoji> Pinterest\n\n'
        "Use the buttons below to try inline mode, tune settings, or share the bot."
    ),

    # Settings
    "settings": (
        "<b>⚙️ Settings</b>\n"
        "Use the buttons below to customize how downloads are sent. "
        "These changes apply only to your account."
    ),
    "settings_private_only": (
        "Settings are available only in private chat. Open DM with the bot to change preferences."
    ),

    # Setting field descriptions
    "field_captions": (
        "<b>📝 Descriptions</b>\n"
        "Show or hide post captions in downloaded media. "
        "Some sources may not provide captions."
    ),
    "field_delete_message": (
        "<b>🗑️ Delete Messages</b>\n"
        "Automatically remove your link once the download is handled."
    ),
    "field_info_buttons": (
        "<b>ℹ️ Info Buttons</b>\n"
        "Toggle additional info buttons under downloaded media."
    ),
    "field_url_button": (
        "<b>🔗 URL Button</b>\n"
        "Show or hide a button with the original post link."
    ),
    "field_audio_button": (
        "<b>🎧 MP3 Button</b>\n"
        "Toggle the Download MP3 button when audio is available."
    ),
    "field_file_button": (
        "<b>📄 File Button</b>\n"
        "Show or hide the Download File button under videos to get original uncompressed files on demand."
    ),
    "field_video_quality": (
        "<b>🎬 Video Quality</b>\n"
        "Select your preferred video download resolution:\n\n"
        "• <b>Best (1080p+)</b>: Maximum possible resolution.\n"
        "• <b>Balanced (720p)</b>: Great balance of quality and speed.\n"
        "• <b>Data Saver (480p)</b>: Faster downloads with minimal data usage."
    ),
    "field_as_document": (
        "<b>📄 Send as File</b>\n"
        "When enabled, videos and photos will be sent as uncompressed documents (.mp4 / .jpg) "
        "preserving 100% original quality."
    ),
    "field_audio_format": (
        "<b>🎵 Audio Format</b>\n"
        "Choose default audio format for music downloads:\n\n"
        "• <b>MP3</b>: Standard universal audio format.\n"
        "• <b>M4A (AAC)</b>: High quality compact format for iOS & Mac.\n"
        "• <b>FLAC / Original</b>: Uncompressed lossless audio where available."
    ),

    # Buttons
    "btn_cancel": "✖️ Cancel",
    "btn_back": "⬅️ Back",
    "btn_next": "Next ➡️",
    "btn_on": "✅ On",
    "btn_off": "❌ Off",
    "btn_settings": "⚙️ Settings",
    "btn_help": "❓ Help",
    "btn_share": "📤 Share",
    "btn_stats": "📊 Statistics",
    "btn_inline": "🔍 Inline mode",

    # Subscriptions
    "must_subscribe": "You must subscribe to the following channels to use the bot:",
    "subscribe_channels": "Subscribe to the following channels:",
    "subscription_status": "Subscription Status",
    "already_subscribed": "✅ Subscribed",
    "not_subscribed": "❌ Not subscribed",

    # Admin
    "admin_panel": "<b>Admin Panel</b>\nSelect buttons to manage.",
    "broadcast_message": "Send Message",
    "manage_subscriptions": "Manage Subscriptions",
    "storage_stats": "Storage Statistics",
    "statistics": "Statistics",

    # Errors & Info
    "error": "An error occurred. Please try again.",
    "no_permission": "You don't have permission.",
    "saved": "✅ Saved",
    "updated": "✅ Updated",
}

def get_text(key: str) -> str:
    return MESSAGES.get(key, key)
