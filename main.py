import asyncio
import hashlib
import os
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Callable, Optional

import httpx
from aiocron import crontab
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums.parse_mode import ParseMode
from aiogram.types import Update
from flask import Flask, abort, jsonify, request
from sqlalchemy import insert as sql_insert

from app_context import set_app_context
from config import (
    API_SECRET,
    BOT_COMMANDS,
    BOT_SESSION_CONNECTION_LIMIT,
    BOT_TOKEN,
    CUSTOM_API_URL,
    HTTP_HEALTH_HOST,
    HTTP_HEALTH_PORT,
    MEASUREMENT_ID,
    OUTPUT_DIR,
    WEBHOOK_SECRET_PATH,
    WEBHOOK_SECRET_TOKEN,
    WEBHOOK_URL,
)
from services.download.queue import shutdown_download_queue
from services.logger import logger as logging
from services.runtime.analytics_status import record_drop as record_analytics_drop
from services.storage.db import AnalyticsEvent, DataBase
from utils.download_manager import close_download_http_clients
from utils.http_client import close_http_session

logging = logging.bind(service="main")

_HEARTBEAT_PATH = "/tmp/bot_heartbeat"
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET_PATH}"


def _write_heartbeat() -> None:
    try:
        with open(_HEARTBEAT_PATH, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception as exc:
        logging.debug("Heartbeat write failed: %s", exc)


async def _heartbeat_loop():
    while True:
        _write_heartbeat()
        await asyncio.sleep(15)


def _get_uptime() -> float:
    try:
        if os.path.exists(_HEARTBEAT_PATH):
            with open(_HEARTBEAT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return time.time() - float(content)
    except Exception:
        pass
    return 0.0


@dataclass(slots=True)
class _AnalyticsPayload:
    user_id: int
    chat_type: str
    action_name: str


@dataclass(slots=True)
class Application:
    session: AiohttpSession
    bot: Bot
    dispatcher: Dispatcher
    db: DataBase


def create_app(
    *,
    bot_token: str = BOT_TOKEN,
    api_url: str = CUSTOM_API_URL,
    database_factory: Callable[[], DataBase] = DataBase,
    session_timeout: int = 600,
    session_limit: int = BOT_SESSION_CONNECTION_LIMIT,
) -> Application:
    session = AiohttpSession(
        limit=max(1, int(session_limit)),
        api=TelegramAPIServer.from_base(api_url),
        timeout=session_timeout,
    )
    default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=bot_token, default=default, session=session)
    dispatcher = Dispatcher()
    db = database_factory()
    os.makedirs("downloads", exist_ok=True)
    return Application(
        session=session,
        bot=bot,
        dispatcher=dispatcher,
        db=db,
    )


_app = create_app()
session = _app.session
bot = _app.bot
dp = _app.dispatcher
db = _app.db


_ANALYTICS_QUEUE_MAXSIZE = 2048
_ANALYTICS_WORKERS = 2
_ANALYTICS_BATCH_SIZE = 25
_ANALYTICS_BATCH_TIMEOUT = 0.5
_ANALYTICS_SEND_CONCURRENCY = 8

_analytics_queue: Optional[asyncio.Queue[Optional[_AnalyticsPayload]]] = None
_analytics_worker_tasks: list[asyncio.Task] = []
_analytics_http_client: Optional[httpx.AsyncClient] = None
_analytics_http_client_lock = asyncio.Lock()


async def _get_analytics_http_client() -> httpx.AsyncClient:
    global _analytics_http_client
    if _analytics_http_client is not None:
        return _analytics_http_client

    async with _analytics_http_client_lock:
        if _analytics_http_client is None:
            _analytics_http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
            )
        return _analytics_http_client


async def _close_analytics_http_client() -> None:
    global _analytics_http_client
    if _analytics_http_client is not None:
        try:
            await _analytics_http_client.aclose()
        except Exception as error:  # pragma: no cover - defensive close
            logging.debug("Failed to close analytics HTTP client: %s", error)
    _analytics_http_client = None


def _build_analytics_identity(user_id: int) -> tuple[str, str, str]:
    salt = f"{BOT_TOKEN}:{MEASUREMENT_ID or 'ga'}"
    digest = hashlib.sha256(f"{salt}:{int(user_id)}".encode("utf-8")).hexdigest()
    client_id = digest
    user_identifier = digest[:32]
    session_id = str(int(digest[:16], 16))
    return client_id, user_identifier, session_id


async def _send_to_google_analytics(payload: _AnalyticsPayload) -> None:
    if not MEASUREMENT_ID or not API_SECRET:
        return

    client_id, user_identifier, session_id = _build_analytics_identity(payload.user_id)
    params = {
        "client_id": client_id,
        "user_id": user_identifier,
        "events": [
            {
                "name": payload.action_name,
                "params": {
                    "chat_type": payload.chat_type,
                    "session_id": session_id,
                    "engagement_time_msec": "1000",
                },
            }
        ],
    }

    client = await _get_analytics_http_client()
    await client.post(
        f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}",
        json=params,
        timeout=10,
    )


async def _persist_analytics_batch(batch: list[_AnalyticsPayload]) -> None:
    if not batch:
        return

    rows = [
        {"user_id": p.user_id, "chat_type": p.chat_type, "action_name": p.action_name}
        for p in batch
    ]

    async with db.SessionLocal() as db_session:
        await db_session.execute(sql_insert(AnalyticsEvent), rows)
        await db_session.commit()


async def _flush_analytics_batch(batch: list[_AnalyticsPayload]) -> None:
    if not batch:
        return

    started_at = asyncio.get_running_loop().time()

    semaphore = asyncio.Semaphore(max(1, _ANALYTICS_SEND_CONCURRENCY))

    async def _send_payload(payload: _AnalyticsPayload) -> None:
        async with semaphore:
            try:
                await _send_to_google_analytics(payload)
            except Exception as error:
                logging.debug(
                    "Failed to send analytics to GA: user_id=%s action=%s error=%s",
                    payload.user_id,
                    payload.action_name,
                    error,
                )

    await asyncio.gather(*(_send_payload(payload) for payload in batch))

    await _persist_analytics_batch(batch)
    logging.perf(
        "analytics_batch_flush",
        duration_ms=(asyncio.get_running_loop().time() - started_at) * 1000.0,
        batch_size=len(batch),
    )


async def _analytics_worker(worker_id: int) -> None:
    queue = _analytics_queue
    if queue is None:
        return

    with logging.context(
        flow="analytics_worker", request_id=f"analytics-worker-{worker_id}"
    ):
        loop = asyncio.get_running_loop()
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break

            batch = [item]
            stop_requested = False
            deadline = loop.time() + _ANALYTICS_BATCH_TIMEOUT

            while len(batch) < _ANALYTICS_BATCH_SIZE:
                timeout = deadline - loop.time()
                if timeout <= 0:
                    break
                try:
                    next_item = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    break

                if next_item is None:
                    stop_requested = True
                    queue.task_done()
                    break

                batch.append(next_item)

            try:
                await _flush_analytics_batch(batch)
            except Exception as error:
                logging.error(
                    "Analytics worker failed: worker=%s error=%s", worker_id, error
                )
            finally:
                for _ in batch:
                    queue.task_done()

            if stop_requested:
                break


async def start_analytics_workers() -> None:
    global _analytics_queue, _analytics_worker_tasks
    if _analytics_queue is not None and _analytics_worker_tasks:
        return

    _analytics_queue = asyncio.Queue(maxsize=_ANALYTICS_QUEUE_MAXSIZE)
    _analytics_worker_tasks = [
        asyncio.create_task(_analytics_worker(idx), name=f"analytics-worker-{idx}")
        for idx in range(_ANALYTICS_WORKERS)
    ]
    logging.event("analytics_workers_started", count=_ANALYTICS_WORKERS)


async def stop_analytics_workers() -> None:
    global _analytics_queue, _analytics_worker_tasks
    queue = _analytics_queue
    if queue is not None:
        await queue.join()
        for _ in _analytics_worker_tasks:
            queue.put_nowait(None)
        if _analytics_worker_tasks:
            await asyncio.gather(*_analytics_worker_tasks, return_exceptions=True)

    _analytics_worker_tasks = []
    _analytics_queue = None
    await _close_analytics_http_client()


async def send_analytics(user_id, chat_type, action_name):
    try:
        payload = _AnalyticsPayload(
            user_id=user_id,
            chat_type=chat_type.value
            if hasattr(chat_type, "value")
            else str(chat_type),
            action_name=action_name,
        )

        queue = _analytics_queue
        if queue is not None:
            try:
                queue.put_nowait(payload)
                return
            except asyncio.QueueFull:
                record_analytics_drop()
                logging.warning(
                    "Analytics queue is full, dropping event: user_id=%s action=%s",
                    user_id,
                    action_name,
                )
                logging.event(
                    "analytics_dropped",
                    level=30,
                    user_id=user_id,
                    chat_type=payload.chat_type,
                    action_name=action_name,
                )
                return

        await _flush_analytics_batch([payload])
    except Exception as error:
        logging.error(
            "Failed to record analytics event: action=%s user_id=%s error=%s",
            action_name,
            user_id,
            error,
        )


# ---------------------------------------------------------------------------
# Background asyncio event loop
#
# Flask (this file's __main__ entrypoint) is a synchronous WSGI app. aiogram
# is fully async. We run one persistent asyncio event loop on a dedicated
# background thread for the whole process lifetime, start the bot/dispatcher
# on it, and hand each incoming Telegram webhook update to that loop via
# `asyncio.run_coroutine_threadsafe`.
# ---------------------------------------------------------------------------

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_bot_ready = threading.Event()
_analytics_started = False


def _run_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


async def _startup() -> None:
    global _analytics_started
    with logging.context(flow="startup", request_id="bot-startup"):
        startup_started_at = asyncio.get_running_loop().time()
        bot_me = await bot.get_me()
        logging.event("bot_startup", bot_username=bot_me.username)
        set_app_context(bot=bot, db=db, send_analytics=send_analytics)
        await db.init_db()
        await start_analytics_workers()
        _analytics_started = True

        import handlers
        import middlewares
        from handlers.admin import clear_downloads_and_notify

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        dp.include_router(handlers.router)

        for middleware_cls in middlewares.__all__:
            middleware = middleware_cls()
            dp.message.outer_middleware(middleware)
            dp.callback_query.outer_middleware(middleware)
            dp.inline_query.outer_middleware(middleware)

        await bot.set_my_commands(commands=BOT_COMMANDS)

        if WEBHOOK_URL:
            webhook_url = WEBHOOK_URL.rstrip("/") + WEBHOOK_PATH
            await bot.set_webhook(
                url=webhook_url,
                secret_token=WEBHOOK_SECRET_TOKEN or None,
                drop_pending_updates=True,
                allowed_updates=dp.resolve_used_update_types(),
            )
            logging.event("webhook_set", webhook_url=webhook_url)
        else:
            logging.event(
                "webhook_url_missing",
                level=30,
                message="WEBHOOK_URL is not set; Telegram webhook was not registered.",
            )

        crontab("0 0 * * *", func=clear_downloads_and_notify, start=True)

        asyncio.create_task(_heartbeat_loop())
        _write_heartbeat()

        logging.perf(
            "bot_startup_duration",
            duration_ms=(asyncio.get_running_loop().time() - startup_started_at)
            * 1000.0,
            bot_username=bot_me.username,
        )
        logging.event("webhook_mode_ready")


async def _shutdown() -> None:
    logging.event("shutdown_starting")
    with suppress(Exception):
        await bot.delete_webhook(drop_pending_updates=False)
    if _analytics_started:
        with suppress(Exception):
            await stop_analytics_workers()
    with suppress(Exception):
        await shutdown_download_queue()
    with suppress(Exception):
        close_download_http_clients()
    with suppress(Exception):
        await close_http_session()
    with suppress(Exception):
        await session.close()
    with suppress(Exception):
        await db.engine.dispose()


def start_background_loop() -> None:
    """Start the asyncio loop thread and run bot startup on it. Idempotent."""
    global _loop, _loop_thread
    if _loop is not None:
        return

    _loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(
        target=_run_event_loop, args=(_loop,), daemon=True, name="bot-event-loop"
    )
    _loop_thread.start()

    future = asyncio.run_coroutine_threadsafe(_startup(), _loop)
    future.result()  # propagate startup exceptions to the main thread
    _bot_ready.set()


def stop_background_loop() -> None:
    global _loop, _loop_thread
    if _loop is None:
        return
    with suppress(Exception):
        asyncio.run_coroutine_threadsafe(_shutdown(), _loop).result(timeout=10)
    _loop.call_soon_threadsafe(_loop.stop)
    if _loop_thread is not None:
        _loop_thread.join(timeout=10)
    _loop = None
    _loop_thread = None


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

flask_app = Flask(__name__)


@flask_app.route("/health", methods=["GET"])
def health_check():
    try:
        uptime = _get_uptime()
        ready = _bot_ready.is_set()
        status_code = 200 if ready else 503
        return jsonify({"status": "ok" if ready else "starting", "uptime_seconds": int(uptime)}), status_code
    except Exception:
        return jsonify({"status": "error"}), 500


@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    if not _bot_ready.is_set() or _loop is None:
        abort(503)

    if WEBHOOK_SECRET_TOKEN:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != WEBHOOK_SECRET_TOKEN:
            abort(401)

    data = request.get_json(force=True, silent=True)
    if data is None:
        abort(400)

    try:
        update = Update.model_validate(data)
    except Exception as exc:
        logging.warning("Failed to parse Telegram update: %s", exc)
        abort(400)

    async def _process() -> None:
        try:
            await dp.feed_update(bot, update)
        except Exception as exc:  # pragma: no cover - defensive
            logging.error("Failed to process update %s: %s", update.update_id, exc)

    asyncio.run_coroutine_threadsafe(_process(), _loop)
    return jsonify({"ok": True}), 200


# Start the bot as soon as the module is imported under a real server
# (Flask dev server via `python main.py`, or a WSGI server like gunicorn
# importing `main:flask_app`), but not on plain `import main` — e.g. when
# pytest imports this module to unit-test helpers. Set BOT_AUTOSTART=0 to
# opt out (used by the test suite and by `container_entrypoint.py`'s own
# module-level checks).
if os.environ.get("BOT_AUTOSTART", "1") != "0":
    start_background_loop()


if __name__ == "__main__":
    if _loop is None:
        start_background_loop()
    try:
        flask_app.run(host=HTTP_HEALTH_HOST, port=HTTP_HEALTH_PORT, debug=False, use_reloader=False, threaded=True)
    finally:
        stop_background_loop()
