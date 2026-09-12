"""Background auto-cleanup scheduler for downloaded media files.

Runs as a periodic asyncio task (started from main.py at startup) rather
than blocking the bot's main event loop. It reads its configuration from
app_settings (admin-controlled via the admin panel) on every tick, so
changes made through the "Storage" admin menu take effect on the next run
without needing a restart.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from services.logger import logger as logging
from services.storage_manager import StorageManager

logging = logging.bind(service="scheduler")

_CHECK_INTERVAL_SECONDS = 15 * 60  # Check every 15 minutes; cheap no-op if disabled.
_scheduler_task: asyncio.Task | None = None


async def _run_auto_cleanup_once(db) -> None:
    if not await db.is_auto_cleanup_enabled():
        return

    ttl_hours = await db.get_auto_cleanup_ttl_hours()
    max_size_mb = await db.get_auto_cleanup_max_size_mb()

    storage_manager = StorageManager()

    try:
        ttl_result = await asyncio.to_thread(
            storage_manager.cleanup_old_files, 7, ttl_hours
        )
        if ttl_result["deleted_files"] > 0:
            logging.event(
                "auto_cleanup_ttl_run",
                deleted_files=ttl_result["deleted_files"],
                freed_mb=ttl_result["freed_mb"],
                ttl_hours=ttl_hours,
            )

        size_result = await asyncio.to_thread(
            storage_manager.cleanup_by_size_limit, max_size_mb
        )
        if size_result["deleted_files"] > 0:
            logging.event(
                "auto_cleanup_size_run",
                deleted_files=size_result["deleted_files"],
                freed_mb=size_result["freed_mb"],
                max_size_mb=max_size_mb,
            )
    except Exception as exc:
        logging.error("Auto cleanup run failed: %s", exc)
        return

    now = datetime.now(timezone.utc)
    next_run = now + timedelta(seconds=_CHECK_INTERVAL_SECONDS)
    try:
        await db.set_auto_cleanup_last_run(now.isoformat())
        await db.set_auto_cleanup_next_run(next_run.isoformat())
    except Exception as exc:
        logging.error("Failed to persist auto cleanup schedule state: %s", exc)


async def _scheduler_loop(db) -> None:
    from services.broadcast_service import BroadcastService
    from app_context import bot

    broadcast_service = BroadcastService(bot, db)

    # Stagger the very first run slightly so it doesn't compete with
    # startup work (webhook registration, analytics workers, etc).
    await asyncio.sleep(30)
    while True:
        try:
            await _run_auto_cleanup_once(db)
        except Exception as exc:
            # Defensive: a bug in one cycle should never kill the loop,
            # since this runs unattended in a background task for the
            # lifetime of the process (important on Render/Web Service
            # deployments where the process may run for days).
            logging.error("Unexpected error in auto cleanup loop: %s", exc)

        try:
            await broadcast_service.process_due_scheduled_broadcasts()
        except Exception as exc:
            logging.error("Unexpected error processing scheduled broadcasts: %s", exc)

        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


def start_auto_cleanup_scheduler(db) -> asyncio.Task:
    """Start the background auto-cleanup loop. Safe to call once at
    startup; returns the created task so callers can keep a reference if
    they want to cancel it (e.g. in tests)."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        return _scheduler_task
    _scheduler_task = asyncio.create_task(
        _scheduler_loop(db), name="auto-cleanup-scheduler"
    )
    logging.event("auto_cleanup_scheduler_started")
    return _scheduler_task


async def run_manual_cleanup_cycle(db) -> dict:
    """Run one cleanup cycle immediately (used by the admin panel's manual
    cleanup buttons) and return a summary."""
    storage_manager = StorageManager()
    ttl_hours = await db.get_auto_cleanup_ttl_hours()
    max_size_mb = await db.get_auto_cleanup_max_size_mb()

    ttl_result = await asyncio.to_thread(
        storage_manager.cleanup_old_files, 7, ttl_hours
    )
    size_result = await asyncio.to_thread(
        storage_manager.cleanup_by_size_limit, max_size_mb
    )

    now = datetime.now(timezone.utc)
    await db.set_auto_cleanup_last_run(now.isoformat())

    return {
        "ttl_deleted": ttl_result["deleted_files"],
        "ttl_freed_mb": ttl_result["freed_mb"],
        "size_deleted": size_result["deleted_files"],
        "size_freed_mb": size_result["freed_mb"],
    }
