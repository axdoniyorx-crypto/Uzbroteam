from __future__ import annotations

import asyncio
import re
import time
import uuid
from typing import Optional

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

import keyboards as kb
import messages as bm
from app_context import bot, db, send_analytics
from config import MAX_FILE_SIZE
from handlers.request_dedupe import claim_message_request
from handlers.utils import (
    get_bot_avatar_thumbnail,
    get_bot_url,
    get_message_text,
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
from services.media.delivery import build_audio_cache_key, deliver_track_as_audio
from utils.download_manager import (
    DownloadQueueBusyError,
    DownloadRateLimitError,
    DownloadTooLargeError,
)

logging = logging.bind(service="music_search")

router = Router()

# Any message containing a link is handled by the platform-specific handlers
# (youtube.py, instagram.py, etc). This handler only fires for plain text
# that looks like a song search query, so it must NOT match URLs.
_URL_REGEX = re.compile(r"https?://|www\.", re.IGNORECASE)
_MIN_QUERY_LENGTH = 2
_MAX_QUERY_LENGTH = 100
_SESSION_TTL_SECONDS = 15 * 60

# In-memory session store: session_id -> (created_at, query, user_id, chat_id, results)
_search_sessions: dict[str, tuple[float, str, int, int, list[dict]]] = {}


def _looks_like_search_query(message: types.Message) -> bool:
    text = get_message_text(message)
    if not text:
        return False
    text = text.strip()
    if not (_MIN_QUERY_LENGTH <= len(text) <= _MAX_QUERY_LENGTH):
        return False
    if _URL_REGEX.search(text):
        return False
    if text.startswith("/"):
        return False
    return True


def _prune_expired_sessions() -> None:
    now = time.monotonic()
    expired = [
        sid for sid, (created_at, *_rest) in _search_sessions.items()
        if now - created_at > _SESSION_TTL_SECONDS
    ]
    for sid in expired:
        _search_sessions.pop(sid, None)


@router.message(F.text.func(lambda text: True) & ~F.text.startswith("/"))
@with_message_logging("music_search", "message")
async def handle_music_search_text(message: types.Message, state: FSMContext):
    """Catch-all for plain text that isn't a supported link and isn't a
    command: treat it as a song search query. Registered after all
    link-specific handlers, so it only fires when nothing else matched.

    Explicitly bails out if the user is mid-flow in some other FSM state
    (e.g. an admin typing a broadcast message) so this doesn't hijack
    unrelated text-input flows."""
    current_state = await state.get_state()
    if current_state is not None:
        return
    if not _looks_like_search_query(message):
        return
    if message.chat.type != "private":
        # Avoid noisy false-positive searches from ordinary group chit-chat.
        return

    query = get_message_text(message).strip()
    business_id = message.business_connection_id
    if await should_skip_duplicate_business_message(
        message, bot, service_name="Music search", logger=logging
    ):
        return

    request_lease = await claim_message_request(message, service="music_search", url=query.lower())
    if request_lease is None:
        return

    logging.info(
        "Music search request: user_id=%s query=%s",
        message.from_user.id,
        query,
    )
    await send_analytics(
        user_id=message.from_user.id,
        chat_type=message.chat.type,
        action_name="music_search",
    )

    status_message: Optional[types.Message] = None
    try:
        await react_to_message(message, "🔍", business_id=business_id)
        status_message = await message.reply(bm.music_search_started(query))

        results = await asyncio.to_thread(search_youtube_tracks, query, 10)
        if not results:
            await safe_edit_text(status_message, bm.music_search_no_results(query))
            return

        _prune_expired_sessions()
        session_id = uuid.uuid4().hex[:12]
        _search_sessions[session_id] = (
            time.monotonic(),
            query,
            message.from_user.id,
            message.chat.id,
            results,
        )

        await safe_edit_text(
            status_message,
            bm.music_search_results(query, results),
            reply_markup=kb.music_search_results_keyboard(session_id, len(results)),
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
        logging.error("Music search failed: query=%s error=%s", query, exc)
        if status_message:
            await safe_edit_text(status_message, bm.music_search_no_results(query))
    finally:
        if request_lease is not None:
            request_lease.finish()


@router.callback_query(F.data.startswith("music_cancel:"))
async def cancel_music_search(call: types.CallbackQuery):
    session_id = call.data.split(":", 1)[1]
    _search_sessions.pop(session_id, None)
    await call.answer()
    await safe_delete_message(call.message)


@router.callback_query(F.data.startswith("music_pick:"))
async def pick_music_search_result(call: types.CallbackQuery):
    _, session_id, index_str = call.data.split(":", 2)
    session = _search_sessions.get(session_id)
    if not session:
        await call.answer(bm.music_search_expired(), show_alert=True)
        return

    _created_at, query, owner_id, _chat_id, results = session
    if call.from_user.id != owner_id:
        await call.answer(bm.music_search_expired(), show_alert=True)
        return

    try:
        index = int(index_str) - 1
        track = results[index]
    except (ValueError, IndexError):
        await call.answer(bm.music_search_invalid_choice(), show_alert=True)
        return

    await call.answer()
    _search_sessions.pop(session_id, None)

    message = call.message
    await safe_edit_text(message, bm.downloading_audio_status())

    business_id = None
    user_settings = await load_user_settings(db, message)
    bot_url = await get_bot_url(bot)

    if not track.get("webpage_url"):
        await safe_edit_text(message, bm.music_search_invalid_choice())
        return

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
            "Music search delivery failed: url=%s error=%s",
            track.get("webpage_url"),
            exc,
        )
        await handle_download_error(message, business_id=business_id)
