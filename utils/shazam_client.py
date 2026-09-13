"""Client for the standalone Shazam recognition microservice.

Mirrors the shape of utils/cobalt_client.py: a thin async wrapper around the
shared aiohttp session that posts a file to the service and returns a small,
already-normalized dict, or None on any failure. Callers don't need to know
anything about the microservice's response schema.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import aiohttp

from services.logger import logger as logging
from utils.http_client import get_http_session

logging = logging.bind(service="shazam_client")


async def recognize_audio_file(
    *,
    base_url: Optional[str],
    api_key: Optional[str],
    file_path: str,
    filename: str,
    timeout: float = 55.0,
) -> Optional[dict[str, Any]]:
    """Upload a local audio/video file to the Shazam service and return the
    matched track dict, or None if there was no match or the request failed.

    Never raises — logs and returns None on any error so callers can show a
    simple "couldn't recognize this" message without their own try/except.
    """
    if not base_url:
        logging.error("SHAZAM_API_URL is not configured")
        return None

    started_at = time.perf_counter()
    endpoint = f"{base_url.rstrip('/')}/recognize"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        session = await get_http_session()
        with open(file_path, "rb") as fh:
            form = aiohttp.FormData()
            form.add_field("file", fh, filename=filename, content_type="application/octet-stream")
            async with session.post(
                endpoint,
                data=form,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 401:
                    logging.error("Shazam service rejected API key (401)")
                    return None
                if resp.status == 413:
                    logging.warning("Shazam service rejected file as too large (413)")
                    return None
                if resp.status == 504:
                    logging.warning("Shazam recognition timed out on the service side")
                    return None
                if resp.status != 200:
                    body_snippet = (await resp.text())[:300]
                    logging.error(
                        "Shazam service error: status=%s body=%s", resp.status, body_snippet
                    )
                    return None

                data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logging.error("Shazam service request failed: error=%s", exc)
        return None
    except Exception as exc:
        logging.exception("Unexpected error calling Shazam service: error=%s", exc)
        return None

    duration_ms = (time.perf_counter() - started_at) * 1000.0
    logging.perf("shazam_recognize", duration_ms=duration_ms, matched=bool(data.get("matched")))

    if not isinstance(data, dict) or not data.get("matched"):
        return None
    track = data.get("track")
    if not isinstance(track, dict):
        return None
    return track
