# TIME-X — Production-ready full-stack watch store

FastAPI + PostgreSQL + responsive static frontend, packaged for production with Docker Compose and Caddy HTTPS.

## Local development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Production

See **[DEPLOY.md](DEPLOY.md)**. The recommended stack is:

- FastAPI + Uvicorn workers
- PostgreSQL 16
- Docker Compose
- Caddy automatic HTTPS
- Persistent media and receipt volumes
- PostgreSQL backup/restore scripts

Production mode refuses to start with SQLite, missing database configuration, missing explicit admin credentials, missing CORS origins, or missing trusted hosts.

## Included modules

The existing storefront/admin modules remain in the release: Dashboard, Products, Orders, Customers, Reviews, Returns, Ledger, Inventory, Brands, Coupons, Delivery Zones, Site Photos, Subscribers, Settings, catalog pages, collections, blogs/gallery, wishlist, account, cart, checkout and receipts.

## Security/deployment changes in this release

- No real `.env` file or SQLite production database is shipped.
- Production requires PostgreSQL.
- Production requires a unique admin password of at least 16 characters.
- Secure, HttpOnly, SameSite cookies are enabled in production.
- Trusted hosts and explicit CORS origins are configurable.
- API documentation is disabled by default in production.
- Security headers and gzip/zstd-compatible proxy compression are enabled.
- PostgreSQL connection health checks and application health checks are included.
- Docker runs the application as a non-root user.
- Media and receipt directories are persistent Docker volumes.
- Caddy handles HTTPS certificates and reverse proxying.
- Backup and restore scripts are included.

For real payments, configure the actual merchant/provider credentials and test the provider's production flow before accepting live orders.
