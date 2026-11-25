from sqlalchemy.orm import Session

from . import models
from .cache_utils import cache_get, cache_set, invalidate_catalog_cache

_SETTINGS_CACHE_KEY = "__site_settings__"
_SETTINGS_TTL_SECONDS = 60.0


def invalidate_settings_cache() -> None:
    invalidate_catalog_cache()


def get_all_settings(db: Session) -> dict[str, str]:
    cached = cache_get(_SETTINGS_CACHE_KEY)
    if cached is not None:
        return cached
    rows = db.query(models.SiteSetting).all()
    data = {row.key: row.value for row in rows}
    cache_set(_SETTINGS_CACHE_KEY, data, ttl=_SETTINGS_TTL_SECONDS)
    return data


def get_setting(db: Session, key: str, default: str = "") -> str:
    return get_all_settings(db).get(key, default)


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.SiteSetting(key=key, value=value))
    invalidate_catalog_cache()
