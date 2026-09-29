#!/usr/bin/env bash
set -euo pipefail

# Run from the project directory. Creates a compressed logical backup on the host.
# Example cron: 15 2 * * * /opt/timex/ops/backup-postgres.sh

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/timexnepal-$STAMP.sql.gz"

set -a
source .env
set +a

docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$FILE"
find "$BACKUP_DIR" -type f -name 'timexnepal-*.sql.gz' -mtime +14 -delete

echo "Created $FILE"
