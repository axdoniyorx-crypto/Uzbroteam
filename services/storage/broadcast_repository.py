from datetime import datetime
from sqlalchemy import func, select, update
from services.logger import logger as logging
from services.storage.models import BroadcastMessage

logging = logging.bind(service="db_broadcasts")


class BroadcastRepositoryMixin:
    async def create_broadcast(
        self,
        message_text: str,
        created_by: int,
        target_type: str = "all",
        image_url: str | None = None,
    ) -> int:
        async with self.SessionLocal() as session:
            broadcast = BroadcastMessage(
                message_text=message_text,
                image_url=image_url,
                created_by=created_by,
                target_type=target_type,
                status="draft",
            )
            session.add(broadcast)
            await session.commit()
            logging.event("broadcast_created", broadcast_id=broadcast.id, target=target_type)
            return broadcast.id

    async def get_broadcast(self, broadcast_id: int) -> dict | None:
        async with self.SessionLocal() as session:
            stmt = select(BroadcastMessage).where(BroadcastMessage.id == broadcast_id)
            result = await session.execute(stmt)
            broadcast = result.scalar()

            if not broadcast:
                return None

            return {
                "id": broadcast.id,
                "message_text": broadcast.message_text,
                "image_url": broadcast.image_url,
                "target_type": broadcast.target_type,
                "status": broadcast.status,
                "scheduled_at": broadcast.scheduled_at,
                "sent_count": broadcast.sent_count,
                "failed_count": broadcast.failed_count,
                "created_at": broadcast.created_at,
                "sent_at": broadcast.sent_at,
            }

    async def schedule_broadcast(self, broadcast_id: int, scheduled_at) -> None:
        async with self.SessionLocal() as session:
            await session.execute(
                update(BroadcastMessage)
                .where(BroadcastMessage.id == broadcast_id)
                .values(scheduled_at=scheduled_at, status="scheduled")
            )
            await session.commit()
            logging.event("broadcast_scheduled", broadcast_id=broadcast_id, scheduled_at=str(scheduled_at))

    async def cancel_broadcast(self, broadcast_id: int) -> None:
        async with self.SessionLocal() as session:
            await session.execute(
                update(BroadcastMessage)
                .where(BroadcastMessage.id == broadcast_id)
                .values(status="cancelled")
            )
            await session.commit()
            logging.event("broadcast_cancelled", broadcast_id=broadcast_id)

    async def get_due_scheduled_broadcasts(self) -> list[dict]:
        async with self.SessionLocal() as session:
            stmt = select(BroadcastMessage).where(
                BroadcastMessage.status == "scheduled",
                BroadcastMessage.scheduled_at <= datetime.utcnow(),
            )
            result = await session.execute(stmt)
            return [
                {
                    "id": b.id,
                    "message_text": b.message_text,
                    "image_url": b.image_url,
                    "target_type": b.target_type,
                }
                for b in result.scalars().all()
            ]

    async def get_broadcast_overview_stats(self) -> dict:
        async with self.SessionLocal() as session:
            stmt = select(
                func.count(BroadcastMessage.id).label("total"),
                func.count(BroadcastMessage.id).filter(BroadcastMessage.status == "sent").label("sent"),
                func.count(BroadcastMessage.id).filter(BroadcastMessage.status == "draft").label("draft"),
                func.count(BroadcastMessage.id).filter(BroadcastMessage.status == "scheduled").label("scheduled"),
                func.coalesce(func.sum(BroadcastMessage.sent_count), 0).label("total_sent_count"),
                func.coalesce(func.sum(BroadcastMessage.failed_count), 0).label("total_failed_count"),
            )
            row = (await session.execute(stmt)).one()
            return {
                "total": int(row.total),
                "sent": int(row.sent),
                "draft": int(row.draft),
                "scheduled": int(row.scheduled),
                "total_sent_count": int(row.total_sent_count),
                "total_failed_count": int(row.total_failed_count),
            }

    async def list_broadcasts(self, status: str | None = None, limit: int = 20) -> list[dict]:
        async with self.SessionLocal() as session:
            query = select(BroadcastMessage).order_by(BroadcastMessage.created_at.desc()).limit(limit)
            if status:
                query = query.where(BroadcastMessage.status == status)
            result = await session.execute(query)
            broadcasts = result.scalars().all()

            return [
                {
                    "id": b.id,
                    "message_text": b.message_text[:50] + "..." if len(b.message_text) > 50 else b.message_text,
                    "target_type": b.target_type,
                    "status": b.status,
                    "sent_count": b.sent_count,
                    "failed_count": b.failed_count,
                    "created_at": b.created_at,
                }
                for b in broadcasts
            ]

    async def send_broadcast(self, broadcast_id: int) -> None:
        async with self.SessionLocal() as session:
            stmt = select(BroadcastMessage).where(BroadcastMessage.id == broadcast_id)
            result = await session.execute(stmt)
            broadcast = result.scalar()

            if broadcast:
                broadcast.status = "sent"
                broadcast.sent_at = datetime.utcnow()
                await session.commit()
                logging.event("broadcast_sent", broadcast_id=broadcast_id)

    async def update_broadcast_stats(self, broadcast_id: int, sent: int, failed: int) -> None:
        async with self.SessionLocal() as session:
            stmt = (
                update(BroadcastMessage)
                .where(BroadcastMessage.id == broadcast_id)
                .values(sent_count=sent, failed_count=failed)
            )
            await session.execute(stmt)
            await session.commit()
            logging.debug(f"Broadcast {broadcast_id} stats updated: sent={sent}, failed={failed}")
