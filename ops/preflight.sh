#!/usr/bin/env bash
set -euo pipefail

fail() { echo "ERROR: $*" >&2; exit 1; }

[[ -f .env ]] || fail "Missing .env. Copy .env.production.example to .env and fill every production value."

set -a
# shellcheck disable=SC1091
source ./.env
set +a

[[ "${APP_ENV:-}" == "production" ]] || fail "APP_ENV must be production."
[[ -n "${DOMAIN:-}" && "${DOMAIN}" != *example.com ]] || fail "Set DOMAIN to your real public hostname."
[[ -n "${POSTGRES_PASSWORD:-}" && ${#POSTGRES_PASSWORD} -ge 20 ]] || fail "POSTGRES_PASSWORD must be at least 20 characters."
[[ -n "${TIMEX_ADMIN_PASSWORD:-}" && ${#TIMEX_ADMIN_PASSWORD} -ge 16 ]] || fail "TIMEX_ADMIN_PASSWORD must be at least 16 characters."
[[ "${TIMEX_ADMIN_PASSWORD}" != "${POSTGRES_PASSWORD}" ]] || fail "Admin and database passwords must be different."
[[ "${CORS_ORIGINS:-}" == "https://${DOMAIN}" ]] || fail "CORS_ORIGINS must exactly equal https://${DOMAIN}."
[[ "${TRUSTED_HOSTS:-}" == *"${DOMAIN}"* ]] || fail "TRUSTED_HOSTS must include ${DOMAIN}."
[[ "${COOKIE_SECURE:-}" == "true" ]] || fail "COOKIE_SECURE must be true in production."
[[ "${ENABLE_API_DOCS:-false}" == "false" ]] || fail "ENABLE_API_DOCS should be false in production."

grep -q '^\.env$' .gitignore || fail ".gitignore must exclude .env."

grep -RIl --exclude-dir=.git --exclude='.env.production.example' --exclude='*.md' \
  -E 'timex-admin-2026|REPLACE_WITH_A_' . 2>/dev/null | grep -v '^./ops/preflight.sh$' && \
  fail "Potential placeholder/default secret found in release files." || true

echo "Preflight checks passed."
