"""Shared helpers for storing/serving uploaded photos as rows in the database
rather than files on disk — the single source of truth for every image the
site uses, so nothing can fall out of sync between the database and a
separate media folder. Used by every upload endpoint across admin.py and
orders.py (kept here, not in either router, to avoid a circular import
between them)."""

import io
import os
import tempfile

from PIL import Image as PILImage, ImageOps
from sqlalchemy.orm import Session

from . import models, config

MEDIA_CACHE_DIR = os.path.join(config.MEDIA_DIR, "cache")


def optimize_image_bytes(
    content: bytes,
    content_type: str | None,
    max_width: int = 1200,
    quality: int = 82,
) -> tuple[bytes, str]:
    """Resize oversized uploads and convert to WebP when smaller.
    Leaves videos, SVGs, GIFs, or already-smaller assets untouched."""
    ct = (content_type or "image/jpeg").lower().strip()
    if not ct.startswith("image/") or ct in ("image/svg+xml", "image/gif"):
        return content, ct
    try:
        with PILImage.open(io.BytesIO(content)) as img:
            img = ImageOps.exif_transpose(img)
            if img.width > max_width:
                new_h = max(1, round(img.height * (max_width / img.width)))
                img = img.resize((max_width, new_h), PILImage.Resampling.LANCZOS)
            has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
            target_mode = "RGBA" if has_alpha else "RGB"
            if img.mode != target_mode:
                img = img.convert(target_mode)
            out = io.BytesIO()
            img.save(out, format="WEBP", quality=quality, method=4)
            webp_bytes = out.getvalue()
            if len(webp_bytes) < len(content):
                return webp_bytes, "image/webp"
            return content, ct
    except Exception:
        return content, ct


def _cache_paths(image_id: int) -> tuple[str, str]:
    return (
        os.path.join(MEDIA_CACHE_DIR, f"{image_id}.bin"),
        os.path.join(MEDIA_CACHE_DIR, f"{image_id}.ct"),
    )


def get_cached_image_file(image_id: int) -> tuple[str, str] | None:
    bin_path, ct_path = _cache_paths(image_id)
    if os.path.isfile(bin_path) and os.path.isfile(ct_path):
        try:
            with open(ct_path, "r", encoding="utf-8") as f:
                ct = f.read().strip() or "image/jpeg"
            return bin_path, ct
        except OSError:
            return None
    return None


def _atomic_write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def write_image_cache(image_id: int, data: bytes, content_type: str) -> str:
    bin_path, ct_path = _cache_paths(image_id)
    _atomic_write(bin_path, data)
    _atomic_write(ct_path, (content_type or "image/jpeg").encode("utf-8"))
    return bin_path


def delete_image_cache(image_id: int) -> None:
    for p in _cache_paths(image_id):
        try:
            os.remove(p)
        except OSError:
            pass


def save_image_to_db(db: Session, content: bytes, content_type: str | None) -> str:
    """Optimize uploaded photo bytes, store in the database, warm the disk cache,
    and return the URL that serves them back."""
    content, ct = optimize_image_bytes(content, content_type)
    image = models.Image(data=content, content_type=ct)
    db.add(image)
    db.flush()  # assigns image.id without committing the caller's transaction yet
    try:
        write_image_cache(image.id, content, ct)
    except OSError:
        pass
    return f"/api/media/image/{image.id}"


def delete_image_by_url(db: Session, url: str | None) -> None:
    """If this URL points to a DB-stored image, remove that row and disk cache too."""
    if not url or "/api/media/image/" not in url:
        return
    try:
        image_id = int(url.rsplit("/", 1)[-1])
    except ValueError:
        return
    db.query(models.Image).filter(models.Image.id == image_id).delete()
    delete_image_cache(image_id)
