# TIME-X Production Release 1.0.0

This package is the production deployment release for the TIME-X watch store. It runs the existing FastAPI storefront/admin application behind Caddy with PostgreSQL and persistent Docker volumes.

## Included

- Storefront and responsive mobile pages
- Product/catalog/cart/checkout/order/receipt flows
- Admin dashboard and management modules
- PostgreSQL production database
- Caddy automatic HTTPS
- Persistent product/site media and receipts
- Container health checks and restart policies
- Secure production cookies and host/CORS controls
- PostgreSQL backup/restore scripts
- Production preflight validation

## Quick deploy

1. Install Docker Engine and the Docker Compose plugin on a Linux VPS.
2. Point your domain's DNS A/AAAA record at the VPS.
3. Copy `.env.production.example` to `.env` and fill in real secrets.
4. Run:

```bash
./ops/preflight.sh
docker compose build --pull
docker compose up -d
```

5. Verify:

```bash
docker compose ps
curl -fsS https://YOUR_DOMAIN/api/health
```

6. Open `https://YOUR_DOMAIN/admin/login.html` and sign in with the admin credentials configured in `.env`.

## Never do this

- Do not commit `.env`.
- Do not use the example credentials.
- Do not expose PostgreSQL port 5432 publicly.
- Do not use SQLite for production.
- Do not accept live payments until your actual payment-provider/merchant configuration is tested.

## Updates

```bash
git pull # if using a private repository
docker compose build --pull app
docker compose up -d --remove-orphans
```

Database, media, receipts, and Caddy certificates live in named Docker volumes and survive normal container recreation.
