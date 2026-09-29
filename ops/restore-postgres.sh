#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 backups/timexnepal-YYYYMMDDTHHMMSSZ.sql.gz" >&2
  exit 1
fi

set -a
source .env
set +a

echo "WARNING: this replaces the current database contents."
read -r -p "Type RESTORE to continue: " confirm
[[ "$confirm" == "RESTORE" ]]

gunzip -c "$1" | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
