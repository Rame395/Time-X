# TIME-X production deployment

This release is prepared for a single production VPS using Docker Compose, PostgreSQL and Caddy. Caddy obtains and renews HTTPS certificates automatically.

## Requirements

- Linux VPS with Docker Engine + Docker Compose plugin
- A domain name pointed at the VPS
- TCP ports 80 and 443 open
- At least 2 GB RAM recommended for a small store
- Persistent disk for PostgreSQL, media and receipts

## 1. Upload the release

```bash
git clone <your-private-repository> /opt/timex
cd /opt/timex
```

Or upload/extract the release archive into `/opt/timex`.

## 2. Create production secrets

```bash
cp .env.production.example .env
nano .env
```

Set:

- `DOMAIN` to the real public hostname.
- `POSTGRES_PASSWORD` to a long random password.
- `TIMEX_ADMIN_PASSWORD` to a unique password of at least 16 characters.
- `CORS_ORIGINS` to the exact `https://DOMAIN` origin.
- `TRUSTED_HOSTS` to the hostname without `https://`.
- SMTP values if you want automatic order/return emails.

Generate passwords with a password manager or:

```bash
openssl rand -base64 32
```

Do not reuse the database password as the admin password.

## 3. DNS

Create an `A` record:

```text
shop.example.com -> YOUR_SERVER_PUBLIC_IP
```

Wait for DNS propagation before starting Caddy.

## 4. Start the stack

```bash
docker compose build --pull
docker compose up -d
```

Check:

```bash
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=100 caddy
```

Caddy will request the TLS certificate automatically.

## 5. First login

Open:

```text
https://YOUR_DOMAIN/admin/login.html
```

Use the credentials from `.env`.

On the first boot, the application creates the schema and seeds the initial catalog/settings. After that, changing `TIMEX_ADMIN_PASSWORD` does **not** change an already-created admin account; change credentials through the application's supported admin/account workflow or directly in the database before exposing it publicly.

## 6. Backups

Test a backup immediately:

```bash
./ops/backup-postgres.sh
```

A simple daily cron entry is:

```cron
15 2 * * * cd /opt/timex && ./ops/backup-postgres.sh >> /var/log/timex-backup.log 2>&1
```

Backups should also be copied off the VPS. A local backup does not protect against disk/server loss.

To restore:

```bash
./ops/restore-postgres.sh backups/timexnepal-YYYYMMDDTHHMMSSZ.sql.gz
```

## 7. Updates

```bash
docker compose build --pull app
docker compose up -d --remove-orphans
```

The PostgreSQL volume and media/receipt volumes persist across container recreation.

## Production checklist

- [ ] Domain A/AAAA records point to the VPS.
- [ ] Ports 80/443 are open; SSH is restricted appropriately.
- [ ] `.env` contains unique production secrets and is not committed.
- [ ] PostgreSQL is used; SQLite is not used in production.
- [ ] Admin password is unique and long.
- [ ] `CORS_ORIGINS` exactly matches the storefront origin.
- [ ] `TRUSTED_HOSTS` contains the production hostname.
- [ ] HTTPS works and redirects/serves securely through Caddy.
- [ ] SMTP test email succeeds if email is required.
- [ ] Product image/video uploads persist after container recreation.
- [ ] Checkout creates an order and receipt.
- [ ] Admin can view/update orders and inventory.
- [ ] A PostgreSQL backup has been created and a restore has been tested.
- [ ] Payment gateway/QR merchant credentials have been configured and tested before accepting real payments.

## Important application notes

The store currently supports the payment workflow implemented in the application (including QR/manual transaction verification where configured). A live payment gateway still requires your merchant account credentials and provider-side webhook/API setup; this deployment package does not invent or fake those credentials.

The app serves the frontend and API from the same FastAPI process, so no frontend build command is required.
