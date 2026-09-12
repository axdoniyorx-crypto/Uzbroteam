import os
from datetime import datetime, timedelta
from pathlib import Path
from services.logger import logger as logging

logging = logging.bind(service="storage_manager")


class StorageManager:
    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = Path(downloads_dir)
        self.downloads_dir.mkdir(exist_ok=True)

    def get_storage_stats(self) -> dict:
        """Get total storage usage statistics"""
        if not self.downloads_dir.exists():
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "oldest_file_date": None,
            }

        total_size = 0
        total_files = 0
        oldest_date = None

        for file_path in self.downloads_dir.rglob("*"):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    total_files += 1

                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if oldest_date is None or mtime < oldest_date:
                        oldest_date = mtime
                except Exception as e:
                    logging.warning(f"Failed to stat {file_path}: {e}")

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file_date": oldest_date,
        }

    def cleanup_old_files(self, days_old: int = 7, hours_old: int | None = None) -> dict:
        """Delete files older than the given age.

        If hours_old is provided it takes precedence over days_old, so the
        admin panel can express TTLs like "24 hours" precisely.
        """
        if hours_old is not None:
            cutoff_date = datetime.now() - timedelta(hours=hours_old)
        else:
            cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_files = 0
        freed_bytes = 0

        if not self.downloads_dir.exists():
            return {
                "deleted_files": 0,
                "freed_bytes": 0,
                "freed_mb": 0,
            }

        for file_path in self.downloads_dir.rglob("*"):
            if file_path.is_file():
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_files += 1
                        freed_bytes += size
                        logging.debug(f"Deleted old file: {file_path}")
                except Exception as e:
                    logging.warning(f"Failed to delete {file_path}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        logging.event(
            "cleanup_completed",
            deleted_files=deleted_files,
            freed_mb=freed_mb,
            days_old=days_old,
            hours_old=hours_old,
        )

        return {
            "deleted_files": deleted_files,
            "freed_bytes": freed_bytes,
            "freed_mb": freed_mb,
        }

    def cleanup_by_size_limit(self, max_size_mb: int) -> dict:
        """Delete oldest files until total size is under limit"""
        current_stats = self.get_storage_stats()
        current_size_mb = current_stats["total_size_mb"]

        if current_size_mb <= max_size_mb:
            return {
                "deleted_files": 0,
                "freed_bytes": 0,
                "freed_mb": 0,
                "reason": "Already under size limit",
            }

        target_bytes = max_size_mb * 1024 * 1024
        deleted_files = 0
        freed_bytes = 0

        files_with_mtime = []
        for file_path in self.downloads_dir.rglob("*"):
            if file_path.is_file():
                try:
                    mtime = file_path.stat().st_mtime
                    size = file_path.stat().st_size
                    files_with_mtime.append((file_path, mtime, size))
                except Exception as e:
                    logging.warning(f"Failed to stat {file_path}: {e}")

        files_with_mtime.sort(key=lambda x: x[1])

        for file_path, _, size in files_with_mtime:
            if current_size_mb - (freed_bytes / (1024 * 1024)) <= max_size_mb:
                break

            try:
                file_path.unlink()
                deleted_files += 1
                freed_bytes += size
                logging.debug(f"Deleted to free space: {file_path}")
            except Exception as e:
                logging.warning(f"Failed to delete {file_path}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        logging.event(
            "cleanup_by_size_completed",
            deleted_files=deleted_files,
            freed_mb=freed_mb,
            max_size_mb=max_size_mb,
        )

        return {
            "deleted_files": deleted_files,
            "freed_bytes": freed_bytes,
            "freed_mb": freed_mb,
        }
