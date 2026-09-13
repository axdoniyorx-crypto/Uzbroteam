from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Optional

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest

import keyboards as kb
import messages as bm
from app_context import bot, db, send_analytics
from config import (
    MAX_FILE_SIZE,
    OUTPUT_DIR,
    SHAZAM_API_KEY,
    SHAZAM_API_URL,
    SHAZAM_RECOGNIZE_TIMEOUT_SECONDS,
    TELEGRAM_FILE_DOWNLOAD_LIMIT,
)
from handlers.request_dedupe import claim_message_request
from handlers.utils import (
    get_bot_avatar_thumbnail,
    get_bot_url,
    handle_download_backpressure_error,
    handle_download_error,
    load_user_settings,
    maybe_delete_user_message,
    react_to_message,
    remove_file,
    retry_async_operation,
    safe_delete_message,
    safe_edit_text,
    send_chat_action_if_needed,
    should_skip_duplicate_business_message,
    with_message_logging,
)
from handlers.youtube import (
    download_mp3_with_ytdlp_metrics,
    get_youtube_video,
    search_youtube_tracks,
)
from services.logger import logger as logging
from services.media.delivery import deliver_track_as_audio
from utils.download_manager import (
    DownloadQueueBusyError,
    DownloadRateLimitError,
    DownloadTooLargeError,
)
from utils.shazam_client import recognize_audio_file

logging = logging.bind(service="shazam")

router = Router()

_SESSION_TTL_SECONDS = 15 * 60

# In-memory session store: session_id -> (created_at, shazam_track, user_id, chat_id)
# shazam_track holds the raw recognition result (title/artist/links) so the
# "download full track" callback can re-search YouTube without re-recognizing.
_shazam_sessions: dict[str, tuple[float, dict, int, int]] = {}


def _prune_expired_sessions() -> None:
    now = time.monotonic()
    expired = [
        sid for sid, (created_at, *_rest) in _shazam_sessions.items()
        if now - created_at > _SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _shazam_sessions.pop(sid, None)


def _pick_recognizable_file(message: types.Message) -> Optional[tuple[str, str, Optional[int]]]:
    """Return (file_id, suggested_filename, file_size) for the first
    recognizable media on this message, or None if there isn't one.

    Order of preference: voice note, audio, video, video note, generic
    document that looks like audio/video by mime type.
    """
    if message.voice:
        return message.voice.file_id, "voice.ogg", message.voice.file_size
    if message.audio:
        filename = message.audio.file_name or "audio.mp3"
        return message.audio.file_id, filename, message.audio.file_size
    if message.video:
        filename = message.video.file_name or "video.mp4"
        return message.video.file_id, filename, message.video.file_size
    if message.video_note:
        return message.video_note.file_id, "video_note.mp4", message.video_note.file_size
    if message.document:
        mime = message.document.mime_type or ""
        if mime.startswith("audio/") or mime.startswith("video/"):
            filename = message.document.file_name or "media.bin"
            return message.document.file_id, filename, message.document.file_size
    return None


@router.message(
    F.voice | F.audio | F.video | F.video_note
    | (F.document.mime_type.startswith("audio/"))
    | (F.document.mime_type.startswith("video/"))
)
@with_message_logging("shazam", "message")
async def handle_shazam_recognize(message: types.Message):
    """Recognize a song from a voice message, audio file, or video clip
    using the standalone Shazam microservice, then offer to download the
    full track via the existing YouTube pipeline."""
    if not SHAZAM_API_URL:
        # Feature not configured on this deployment: stay silent rather than
        # confuse users with an error for something they didn't ask for by
        # name (this handler fires passively on any voice/video message).
        logging.debug("SHAZAM_API_URL not configured; skipping recognition")
        return

    picked = _pick_recognizable_file(message)
    if not picked:
        return
    file_id, suggested_filename, file_size = picked

    if file_size and file_size > TELEGRAM_FILE_DOWNLOAD_LIMIT:
        await message.reply(bm.shazam_file_too_large())
        return

    business_id = message.business_connection_id
    if await should_skip_duplicate_business_message(
        message, bot, service_name="Shazam recognition", logger=logging
    ):
        return

    dedupe_key = f"shazam:{file_id}"
    request_lease = await claim_message_request(message, service="shazam", url=dedupe_key)
    if request_lease is None:
        return

    logging.info(
        "Shazam recognition request: user_id=%s file_id=%s size=%s",
        message.from_user.id,
        file_id,
        file_size,
    )
    await send_analytics(
        user_id=message.from_user.id,
        chat_type=message.chat.type,
        action_name="shazam_recognize",
    )

    status_message: Optional[types.Message] = None
    local_path: Optional[str] = None
    try:
        await react_to_message(message, "🎧", business_id=business_id)
        status_message = await message.reply(bm.shazam_recognizing_status())

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex[:12]}_{suggested_filename}"
        local_path = os.path.join(OUTPUT_DIR, unique_name)

        try:
            with open(local_path, "wb") as destination:
                await asyncio.wait_for(
                    bot.download(file_id, destination=destination),
                    timeout=60,
                )
        except asyncio.TimeoutError:
            await safe_edit_text(status_message, bm.shazam_no_match())
            return
        except TelegramBadRequest as exc:
            # Typically "file is too big" for files close to the 20MB
            # boundary that slipped past the file_size pre-check above.
            logging.warning("Telegram file download failed: error=%s", exc)
            await safe_edit_text(status_message, bm.shazam_file_too_large())
            return

        track = await recognize_audio_file(
            base_url=SHAZAM_API_URL,
            api_key=SHAZAM_API_KEY,
            file_path=local_path,
            filename=suggested_filename,
            timeout=SHAZAM_RECOGNIZE_TIMEOUT_SECONDS,
        )

        if not track:
            await safe_edit_text(status_message, bm.shazam_no_match())
            request_lease.mark_success()
            return

        _prune_expired_sessions()
        session_id = uuid.uuid4().hex[:12]
        _shazam_sessions[session_id] = (
            time.monotonic(),
            track,
            message.from_user.id,
            message.chat.id,
        )

        await safe_edit_text(
            status_message,
            bm.shazam_match_found(track),
            reply_markup=kb.shazam_result_keyboard(session_id),
        )
        request_lease.mark_success()
    except (DownloadRateLimitError, DownloadQueueBusyError, DownloadTooLargeError) as exc:
        await handle_download_backpressure_error(
            exc,
            message=message,
            show_service_status=True,
            too_large_text=bm.audio_too_large(),
        )
    except Exception as exc:
        logging.error("Shazam recognition failed: file_id=%s error=%s", file_id, exc)
        if status_message:
            await safe_edit_text(status_message, bm.shazam_no_match())
    finally:
        if request_lease is not None:
            request_lease.finish()
        if local_path:
            await remove_file(local_path)


@router.callback_query(F.data.startswith("shazam_cancel:"))
async def cancel_shazam_result(call: types.CallbackQuery):
    session_id = call.data.split(":", 1)[1]
    _shazam_sessions.pop(session_id, None)
    await call.answer()
    await safe_delete_message(call.message)


@router.callback_query(F.data.startswith("shazam_download:"))
async def download_shazam_track(call: types.CallbackQuery):
    session_id = call.data.split(":", 1)[1]
    session = _shazam_sessions.get(session_id)
    if not session:
        await call.answer(bm.music_search_expired(), show_alert=True)
        return

    _created_at, shazam_track, owner_id, _chat_id = session
    if call.from_user.id != owner_id:
        await call.answer(bm.music_search_expired(), show_alert=True)
        return

    await call.answer()
    _shazam_sessions.pop(session_id, None)

    message = call.message
    await safe_edit_text(message, bm.downloading_audio_status())

    business_id = None
    user_settings = await load_user_settings(db, message)
    bot_url = await get_bot_url(bot)

    title = shazam_track.get("title") or ""
    artist = shazam_track.get("artist") or ""
    query = f"{title} {artist}".strip()
    if not query:
        await safe_edit_text(message, bm.music_search_invalid_choice())
        return

    try:
        results = await asyncio.to_thread(search_youtube_tracks, query, 1)
    except Exception as exc:
        logging.error("YouTube lookup for Shazam track failed: query=%s error=%s", query, exc)
        results = None

    if not results:
        await safe_edit_text(message, bm.music_search_no_results(query))
        return

    track = results[0]

    async def _on_missing_text():
        await handle_download_error(message, business_id=business_id)

    try:
        await deliver_track_as_audio(
            message=message,
            track=track,
            unique_id=session_id,
            bot=bot,
            db_service=db,
            max_file_size=MAX_FILE_SIZE,
            bot_url=bot_url,
            business_id=business_id,
            status_uploading_text=bm.uploading_status(),
            too_large_text=bm.audio_too_large(),
            on_missing_text_fn=_on_missing_text,
            caption_fn=lambda _post_caption: bm.captions(user_settings["captions"], None, bot_url),
            send_chat_action_fn=send_chat_action_if_needed,
            safe_edit_text_fn=safe_edit_text,
            get_bot_avatar_thumbnail_fn=get_bot_avatar_thumbnail,
            remove_file_fn=remove_file,
            retry_async_operation_fn=retry_async_operation,
            get_youtube_video_fn=get_youtube_video,
            download_mp3_fn=download_mp3_with_ytdlp_metrics,
        )
        await maybe_delete_user_message(message, user_settings["delete_message"])
    except (DownloadRateLimitError, DownloadQueueBusyError, DownloadTooLargeError) as exc:
        await handle_download_backpressure_error(
            exc,
            message=message,
            show_service_status=True,
            too_large_text=bm.audio_too_large(),
        )
    except asyncio.TimeoutError:
        await handle_download_error(message, business_id=business_id)
    except Exception as exc:
        logging.error(
            "Shazam track delivery failed: url=%s error=%s",
            track.get("webpage_url"),
            exc,
        )
        await handle_download_error(message, business_id=business_id)
