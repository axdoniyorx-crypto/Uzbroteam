from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.logger import logger as logging
from services.storage.models import AppSetting, MANDATORY_SUBSCRIPTION_TOGGLE_KEY

logging = logging.bind(service="db_app_settings")

_TRUE_VALUES = {"1", "true", "on", "yes"}

# Keys used in app_settings for storage/auto-cleanup and bot-wide toggles.
OPTIONAL_CHANNEL_TOGGLE_KEY = "optional_channel_enabled"
AUTO_CLEANUP_ENABLED_KEY = "auto_cleanup_enabled"
AUTO_CLEANUP_TTL_HOURS_KEY = "auto_cleanup_ttl_hours"
AUTO_CLEANUP_MAX_SIZE_MB_KEY = "auto_cleanup_max_size_mb"
AUTO_CLEANUP_LAST_RUN_KEY = "auto_cleanup_last_run_at"
AUTO_CLEANUP_NEXT_RUN_KEY = "auto_cleanup_next_run_at"
BOT_ENABLED_KEY = "bot_enabled"
WELCOME_MESSAGE_KEY = "welcome_message_text"

DEFAULT_AUTO_CLEANUP_TTL_HOURS = 24
DEFAULT_AUTO_CLEANUP_MAX_SIZE_MB = 2048


class AppSettingsRepositoryMixin:
    async def get_app_setting(self, key: str, default: str | None = None) -> str | None:
        async with self.SessionLocal() as session:
            stmt = select(AppSetting).where(AppSetting.key == key)
            result = await session.execute(stmt)
            row = result.scalar()
            return row.value if row else default

    async def set_app_setting(self, key: str, value: str) -> None:
        async with self.SessionLocal() as session:
            if self._dialect_name == "postgresql":
                stmt = pg_insert(AppSetting).values(key=key, value=value)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[AppSetting.key],
                    set_={"value": value},
                )
                await session.execute(stmt)
            else:
                existing = await session.execute(
                    select(AppSetting).where(AppSetting.key == key)
                )
                row = existing.scalar()
                if row:
                    row.value = value
                else:
                    session.add(AppSetting(key=key, value=value))
            await session.commit()
            logging.event("app_setting_updated", key=key, value=value)

    async def get_app_settings_bulk(self, keys: list[str]) -> dict[str, str | None]:
        """Fetch several keys in a single round trip."""
        async with self.SessionLocal() as session:
            stmt = select(AppSetting).where(AppSetting.key.in_(keys))
            result = await session.execute(stmt)
            rows = {row.key: row.value for row in result.scalars().all()}
            return {key: rows.get(key) for key in keys}

    async def is_mandatory_subscription_enabled(self) -> bool:
        """Global on/off switch for the mandatory-subscription feature.

        Defaults to True (enabled) when no explicit setting has been
        stored yet, preserving existing behaviour for upgrades.
        """
        value = await self.get_app_setting(MANDATORY_SUBSCRIPTION_TOGGLE_KEY, default="on")
        return (value or "on").strip().lower() in _TRUE_VALUES

    async def set_mandatory_subscription_enabled(self, enabled: bool) -> None:
        await self.set_app_setting(
            MANDATORY_SUBSCRIPTION_TOGGLE_KEY, "on" if enabled else "off"
        )

    async def is_optional_channel_enabled(self) -> bool:
        """Global on/off switch for the optional (non-mandatory) channel
        promo feature. Defaults to on."""
        value = await self.get_app_setting(OPTIONAL_CHANNEL_TOGGLE_KEY, default="on")
        return (value or "on").strip().lower() in _TRUE_VALUES

    async def set_optional_channel_enabled(self, enabled: bool) -> None:
        await self.set_app_setting(
            OPTIONAL_CHANNEL_TOGGLE_KEY, "on" if enabled else "off"
        )

    async def get_welcome_message(self) -> str | None:
        """Custom admin-configured /start welcome message text, if set.

        Returns None when the admin hasn't overridden it, so callers can
        fall back to the built-in default text.
        """
        value = await self.get_app_setting(WELCOME_MESSAGE_KEY, default=None)
        if value is None:
            return None
        value = value.strip()
        return value or None

    async def set_welcome_message(self, text: str) -> None:
        await self.set_app_setting(WELCOME_MESSAGE_KEY, text)

    async def reset_welcome_message(self) -> None:
        """Remove the custom welcome message, reverting to the default."""
        async with self.SessionLocal() as session:
            stmt = select(AppSetting).where(AppSetting.key == WELCOME_MESSAGE_KEY)
            result = await session.execute(stmt)
            row = result.scalar()
            if row:
                await session.delete(row)
                await session.commit()
                logging.event("app_setting_reset", key=WELCOME_MESSAGE_KEY)

    async def is_bot_enabled(self) -> bool:
        """Global bot on/off switch. Defaults to on."""
        value = await self.get_app_setting(BOT_ENABLED_KEY, default="on")
        return (value or "on").strip().lower() in _TRUE_VALUES

    async def set_bot_enabled(self, enabled: bool) -> None:
        await self.set_app_setting(BOT_ENABLED_KEY, "on" if enabled else "off")

    async def is_auto_cleanup_enabled(self) -> bool:
        value = await self.get_app_setting(AUTO_CLEANUP_ENABLED_KEY, default="on")
        return (value or "on").strip().lower() in _TRUE_VALUES

    async def set_auto_cleanup_enabled(self, enabled: bool) -> None:
        await self.set_app_setting(AUTO_CLEANUP_ENABLED_KEY, "on" if enabled else "off")

    async def get_auto_cleanup_ttl_hours(self) -> int:
        value = await self.get_app_setting(
            AUTO_CLEANUP_TTL_HOURS_KEY, default=str(DEFAULT_AUTO_CLEANUP_TTL_HOURS)
        )
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return DEFAULT_AUTO_CLEANUP_TTL_HOURS

    async def set_auto_cleanup_ttl_hours(self, hours: int) -> None:
        await self.set_app_setting(AUTO_CLEANUP_TTL_HOURS_KEY, str(max(1, int(hours))))

    async def get_auto_cleanup_max_size_mb(self) -> int:
        value = await self.get_app_setting(
            AUTO_CLEANUP_MAX_SIZE_MB_KEY, default=str(DEFAULT_AUTO_CLEANUP_MAX_SIZE_MB)
        )
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return DEFAULT_AUTO_CLEANUP_MAX_SIZE_MB

    async def set_auto_cleanup_max_size_mb(self, size_mb: int) -> None:
        await self.set_app_setting(
            AUTO_CLEANUP_MAX_SIZE_MB_KEY, str(max(1, int(size_mb)))
        )

    async def get_auto_cleanup_schedule(self) -> dict[str, str | None]:
        values = await self.get_app_settings_bulk(
            [AUTO_CLEANUP_LAST_RUN_KEY, AUTO_CLEANUP_NEXT_RUN_KEY]
        )
        return {
            "last_run_at": values.get(AUTO_CLEANUP_LAST_RUN_KEY),
            "next_run_at": values.get(AUTO_CLEANUP_NEXT_RUN_KEY),
        }

    async def set_auto_cleanup_last_run(self, iso_timestamp: str) -> None:
        await self.set_app_setting(AUTO_CLEANUP_LAST_RUN_KEY, iso_timestamp)

    async def set_auto_cleanup_next_run(self, iso_timestamp: str) -> None:
        await self.set_app_setting(AUTO_CLEANUP_NEXT_RUN_KEY, iso_timestamp)
