import time
from sqlalchemy.orm import Session

from . import models

_SETTINGS_CACHE: dict[str, str] | None = None
_SETTINGS_CACHE_EXPIRES: float = 0.0
_SETTINGS_TTL_SECONDS = 60.0


def invalidate_settings_cache() -> None:
    global _SETTINGS_CACHE, _SETTINGS_CACHE_EXPIRES
    _SETTINGS_CACHE = None
    _SETTINGS_CACHE_EXPIRES = 0.0


def get_all_settings(db: Session) -> dict[str, str]:
    global _SETTINGS_CACHE, _SETTINGS_CACHE_EXPIRES
    now = time.monotonic()
    if _SETTINGS_CACHE is not None and now < _SETTINGS_CACHE_EXPIRES:
        return _SETTINGS_CACHE
    rows = db.query(models.SiteSetting).all()
    data = {row.key: row.value for row in rows}
    _SETTINGS_CACHE = data
    _SETTINGS_CACHE_EXPIRES = now + _SETTINGS_TTL_SECONDS
    return data


def get_setting(db: Session, key: str, default: str = "") -> str:
    return get_all_settings(db).get(key, default)


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.SiteSetting(key=key, value=value))
    invalidate_settings_cache()
