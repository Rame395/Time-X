import os
import time
from typing import Any

from . import config

VERSION_FILE = os.path.join(config.MEDIA_DIR, "cache", ".catalog_version")

_CACHE: dict[str, tuple[float, Any]] = {}
_LAST_VERSION_MTIME: int = 0


def _sync_version() -> None:
    global _LAST_VERSION_MTIME
    try:
        mtime = os.stat(VERSION_FILE).st_mtime_ns
    except Exception:
        mtime = 0
    if mtime != _LAST_VERSION_MTIME:
        _CACHE.clear()
        _LAST_VERSION_MTIME = mtime


def cache_get(key: str) -> Any | None:
    _sync_version()
    entry = _CACHE.get(key)
    if entry is None:
        return None
    expires, value = entry
    if time.monotonic() >= expires:
        _CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl: float = 300.0) -> None:
    _sync_version()
    _CACHE[key] = (time.monotonic() + ttl, value)


def invalidate_catalog_cache() -> None:
    global _LAST_VERSION_MTIME
    _CACHE.clear()
    try:
        os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(str(time.time_ns()))
        _LAST_VERSION_MTIME = os.stat(VERSION_FILE).st_mtime_ns
    except Exception:
        pass
