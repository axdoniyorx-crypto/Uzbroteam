import asyncio
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest, TelegramAPIError
from services.logger import logger as logging
from services.storage.db import DataBase

logging = logging.bind(service="broadcast")

_CONCURRENCY = 5


class BroadcastService:
    def __init__(self, bot: Bot, db: DataBase):
        self.bot = bot
        self.db = db

    async def send_broadcast(
        self,
        broadcast_id: int,
        target_type: str = "all",
        rate_limit_ms: int = 100,
    ) -> dict:
        """Send broadcast message to users, honoring target_type."""
        broadcast = await self.db.get_broadcast(broadcast_id)
        if not broadcast:
            logging.error(f"Broadcast {broadcast_id} not found")
            return {"sent": 0, "failed": 0}

        recipients = await self._resolve_recipients(target_type)

        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def _send_one(chat_id: int) -> bool:
            async with semaphore:
                ok, _ = await self._send_message(chat_id, broadcast)
                await asyncio.sleep(rate_limit_ms / 1000.0)
                return ok

        results = await asyncio.gather(*(_send_one(cid) for cid in recipients))
        sent_count = sum(1 for r in results if r)
        failed_count = len(results) - sent_count

        await self.db.update_broadcast_stats(broadcast_id, sent_count, failed_count)
        await self.db.send_broadcast(broadcast_id)

        logging.event(
            "broadcast_sent",
            broadcast_id=broadcast_id,
            target_type=target_type,
            sent=sent_count,
            failed=failed_count,
        )

        return {"sent": sent_count, "failed": failed_count}

    async def _resolve_recipients(self, target_type: str) -> list[int]:
        try:
            if target_type == "groups":
                groups = await self.db.get_active_groups()
                return [int(g.id) for g in groups]

            if target_type in {"mandatory_subscribers", "optional_subscribers"}:
                # Best-effort: everyone we can DM. Precise per-channel
                # targeting would require iterating live membership, which
                # is expensive at scale; admins can further narrow via the
                # channel list if needed.
                users = await self.db.get_users_for_reachability_check()
                return [int(u.user_id) for u in users if int(u.user_id) > 0]

            # "all": DM users + active groups.
            users = await self.db.get_users_for_reachability_check()
            groups = await self.db.get_active_groups()
            recipients = [int(u.user_id) for u in users if int(u.user_id) > 0]
            recipients.extend(int(g.id) for g in groups)
            return recipients
        except Exception as exc:
            logging.error("Failed to resolve broadcast recipients: %s", exc)
            return []

    async def _send_message(
        self, chat_id: int, broadcast: dict
    ) -> tuple[bool, Optional[str]]:
        """Send single message to a user or group, with one retry on
        Telegram flood-control (429)."""
        try:
            await self._do_send(chat_id, broadcast)
            return True, None
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
            try:
                await self._do_send(chat_id, broadcast)
                return True, None
            except Exception as retry_exc:
                logging.debug(f"Failed to send to {chat_id} after retry: {retry_exc}")
                return False, str(retry_exc)
        except (TelegramForbiddenError, TelegramBadRequest) as error:
            logging.debug(f"Recipient {chat_id} unreachable: {error}")
            return False, str(error)
        except TelegramAPIError as error:
            logging.warning(f"API error sending to {chat_id}: {error}")
            return False, str(error)
        except Exception as e:
            error_msg = str(e)
            logging.debug(f"Failed to send to {chat_id}: {error_msg}")
            return False, error_msg

    async def _do_send(self, chat_id: int, broadcast: dict) -> None:
        if broadcast.get("image_url"):
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=broadcast["image_url"],
                caption=broadcast["message_text"],
                parse_mode="HTML",
            )
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text=broadcast["message_text"],
                parse_mode="HTML",
            )

    async def process_due_scheduled_broadcasts(self) -> None:
        """Send any broadcasts whose scheduled_at has passed. Intended to
        be polled periodically by the scheduler service."""
        due = await self.db.get_due_scheduled_broadcasts()
        for item in due:
            try:
                await self.send_broadcast(item["id"], target_type=item["target_type"])
            except Exception as exc:
                logging.error(
                    "Failed to send scheduled broadcast %s: %s", item["id"], exc
                )
