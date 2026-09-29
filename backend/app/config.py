import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "media")

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

ENVIRONMENT = os.environ.get("APP_ENV", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT in {"production", "prod"}

# --- Store / brand settings ---
WHATSAPP_DEFAULT = os.environ.get("TIMEX_WHATSAPP_NUMBER", "9779768785693")
SESSION_COOKIE_NAME = "timexnepal_admin_session"
CART_COOKIE_NAME = "timexnepal_cart"
CUSTOMER_SESSION_COOKIE_NAME = "timexnepal_customer_session"
WISHLIST_COOKIE_NAME = "timexnepal_wishlist_guest"
SESSION_TTL_DAYS = int(os.environ.get("ADMIN_SESSION_TTL_DAYS", "7"))
CUSTOMER_SESSION_TTL_DAYS = int(os.environ.get("CUSTOMER_SESSION_TTL_DAYS", "30"))

# Cookies are secure in production and remain usable over plain HTTP in local dev.
COOKIE_SECURE = _env_bool("COOKIE_SECURE", IS_PRODUCTION)
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None

# --- Default admin account (used only if the DB has no admin yet) ---
DEFAULT_ADMIN_USERNAME = os.environ.get("TIMEX_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("TIMEX_ADMIN_PASSWORD", "dev-only-change-me-please")

# --- Database ---
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# --- CORS ---
_cors_raw = os.environ.get("CORS_ORIGINS", "")
CORS_ORIGINS = [item.strip() for item in _cors_raw.split(",") if item.strip()]
if not CORS_ORIGINS and not IS_PRODUCTION:
    CORS_ORIGINS = [
        "http://127.0.0.1:8000", "http://localhost:8000",
        "http://127.0.0.1:5500", "http://localhost:5500",
    ]

# --- SMTP ---
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "TIME-X")

# --- API/docs hardening ---
ENABLE_API_DOCS = _env_bool("ENABLE_API_DOCS", not IS_PRODUCTION)
TRUSTED_HOSTS = [h.strip() for h in os.environ.get("TRUSTED_HOSTS", "").split(",") if h.strip()]
if "127.0.0.1" not in TRUSTED_HOSTS:
    TRUSTED_HOSTS.append("127.0.0.1")

# Production must never silently fall back to development credentials/storage.
if IS_PRODUCTION:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be set when APP_ENV=production")
    if DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("Production deployments must use PostgreSQL, not SQLite")
    if not DEFAULT_ADMIN_USERNAME or not DEFAULT_ADMIN_PASSWORD:
        raise RuntimeError("TIMEX_ADMIN_USERNAME and TIMEX_ADMIN_PASSWORD must be set in production")
    if DEFAULT_ADMIN_PASSWORD in {"admin", "password", "changeme"} or DEFAULT_ADMIN_PASSWORD.startswith("timex-admin-") or len(DEFAULT_ADMIN_PASSWORD) < 16:
        raise RuntimeError("TIMEX_ADMIN_PASSWORD must be a unique password of at least 16 characters")
    if not CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must contain your production origin(s)")
    if not TRUSTED_HOSTS:
        raise RuntimeError("TRUSTED_HOSTS must contain your production hostname(s)")
