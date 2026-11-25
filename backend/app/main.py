import html
import json
import os
import sys
from contextlib import asynccontextmanager, contextmanager

from dotenv import load_dotenv
# Load backend/.env before importing config/database — those modules read os.environ
# at import time, so this must happen first or every .env setting is silently ignored.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from . import models, config
from .cache_utils import invalidate_catalog_cache
from .database import engine, SessionLocal
from .seed import seed_if_empty, ensure_unisex_category, ensure_default_departments, ensure_default_delivery_zones, ensure_default_brand_assets, ensure_carried_brands, ensure_display_rank_column
from .routers import products, cart, orders, admin, customers

FRONTEND_DIR = os.path.join(os.path.dirname(config.BASE_DIR), "frontend")

# fcntl is Unix-only (Linux/macOS) — not available on Windows. The lock only matters
# when running multiple worker processes (`uvicorn --workers N`); on Windows, or any
# platform without fcntl, we fall back to no locking at all, which is exactly correct
# for the default single-process run and just means multi-worker startup on Windows
# would need its own coordination (e.g. seed the DB once before starting workers).
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


@contextmanager
def _startup_lock():
    if not HAS_FCNTL:
        yield
        return
    lock_path = os.path.join(config.BASE_DIR, ".startup.lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Guards schema creation + seeding with a cross-process file lock on platforms
    # that support it. Needed because `uvicorn --workers N` starts N processes that
    # each run this lifespan concurrently; without the lock, two workers can both see
    # "table doesn't exist yet" and race to CREATE TABLE, crashing every worker but
    # the first. Under a single process (the default `uvicorn app.main:app`) this is
    # uncontended and adds no real delay.
    with _startup_lock():
        models.Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            ensure_display_rank_column(db)
            seed_if_empty(db)
            ensure_unisex_category(db)
            ensure_default_departments(db)
            ensure_default_delivery_zones(db)
            ensure_default_brand_assets(db)
            ensure_carried_brands(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="TIME-X API",
    lifespan=lifespan,
    docs_url="/docs" if config.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if config.ENABLE_API_DOCS else None,
)

# Allows the API to be called from a separate local dev server (e.g. VS Code's Live
# Server on :5500) instead of only from this same FastAPI process. Harmless in
# production since it's restricted to these specific local origins.
if config.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.TRUSTED_HOSTS)

SKIP_GZIP_EXTS = (
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico",
    ".mp4", ".webm", ".mov", ".woff2", ".woff", ".pdf",
)


class SmartGZipMiddleware:
    """Skip GZip on already-compressed media (images/videos) so CPU isn't wasted."""
    def __init__(self, app, minimum_size: int = 1000):
        self.app = app
        self.gzip_app = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = (scope.get("path") or "").lower()
            if path.startswith(("/api/media/", "/media/")) or path.endswith(SKIP_GZIP_EXTS):
                await self.app(scope, receive, send)
                return
        await self.gzip_app(scope, receive, send)


app.add_middleware(SmartGZipMiddleware, minimum_size=1000)


class SecurityAndCacheMiddleware:
    """Pure ASGI security headers + admin mutation cache invalidation (zero streaming buffer overhead)."""
    _SECURITY_HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"SAMEORIGIN"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    ]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = (scope.get("method") or "GET").upper()
        path = scope.get("path") or ""
        is_admin_mutation = method in ("POST", "PUT", "PATCH", "DELETE") and path.startswith("/api/admin/")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                existing = {k.lower() for k, _ in headers}
                for k, v in self._SECURITY_HEADERS:
                    if k not in existing:
                        headers.append((k, v))
                if config.IS_PRODUCTION and b"strict-transport-security" not in existing:
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                message = {**message, "headers": headers}

                status = message.get("status", 0)
                if is_admin_mutation and 200 <= status < 300:
                    try:
                        invalidate_catalog_cache()
                    except Exception:
                        pass
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(SecurityAndCacheMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(customers.router)


@app.get("/api/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"ok": True, "service": "TIME-X API", "environment": config.ENVIRONMENT}

os.makedirs(config.MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=config.MEDIA_DIR), name="media")

_INDEX_HTML_PATH = os.path.join(FRONTEND_DIR, "index.html")
_INDEX_HTML_CACHE: tuple[int, str] | None = None


def _read_index_html() -> str:
    global _INDEX_HTML_CACHE
    mtime = os.stat(_INDEX_HTML_PATH).st_mtime_ns
    if _INDEX_HTML_CACHE is not None and _INDEX_HTML_CACHE[0] == mtime:
        return _INDEX_HTML_CACHE[1]
    with open(_INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    _INDEX_HTML_CACHE = (mtime, content)
    return content


def _thumb_href(url: str, width: int = 480) -> str:
    if "/api/media/image/" in url and "?" not in url:
        return f"{url}?w={width}"
    return url


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def serve_homepage():
    base_html = _read_index_html()
    try:
        db = SessionLocal()
        try:
            payload = products.build_homepage_payload(db)
        finally:
            db.close()

        preloads: list[str] = []
        heroes = (payload.get("site_images") or {}).get("homepage_hero") or []
        if heroes and heroes[0].get("url"):
            hero_url = html.escape(str(heroes[0]["url"]), quote=True)
            preloads.append(f'<link rel="preload" as="image" href="{hero_url}" fetchpriority="high"/>')

        for card in (payload.get("featured") or [])[:4]:
            img_url = card.get("primary_image")
            if img_url:
                thumb = html.escape(_thumb_href(str(img_url), 480), quote=True)
                preloads.append(f'<link rel="preload" as="image" href="{thumb}"/>')

        serialized = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
        injection = "".join(preloads) + f"<script>window.__INITIAL_HOMEPAGE__={serialized};</script>"
        if "<head>" in base_html:
            injected_html = base_html.replace("<head>", f"<head>\n{injection}", 1)
        else:
            injected_html = base_html
        return HTMLResponse(
            injected_html,
            headers={"Cache-Control": "public, max-age=30, stale-while-revalidate=60"},
        )
    except Exception:
        return HTMLResponse(
            base_html,
            headers={"Cache-Control": "public, max-age=30, stale-while-revalidate=60"},
        )


# Serves the whole static frontend (index.html, men.html, cart.html, admin/, ...).
# Mounted last so it never shadows the /api/* and /media/* routes above.
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")



