import os
import sys
from contextlib import asynccontextmanager, contextmanager

from dotenv import load_dotenv
# Load backend/.env before importing config/database — those modules read os.environ
# at import time, so this must happen first or every .env setting is silently ignored.
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from . import models, config
from .database import engine, SessionLocal
from .seed import seed_if_empty, ensure_unisex_category, ensure_default_departments, ensure_default_delivery_zones, ensure_default_brand_assets, ensure_carried_brands
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

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if config.IS_PRODUCTION:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

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

# Serves the whole static frontend (index.html, men.html, cart.html, admin/, ...).
# Mounted last so it never shadows the /api/* and /media/* routes above.
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
