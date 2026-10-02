#!/usr/bin/env bash
# Nightly database backup. Writes a compressed dump and keeps the newest 30.
# Example cron (2:15 am):  15 2 * * * cd /path/to/lawn-app && ./scripts/backup.sh
# Copy the backups folder to a second location (another disk, NAS, or cloud drive).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
out="backups/lawn-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U lawn lawn | gzip > "$out"
echo "Wrote $out"
ls -1t backups/lawn-*.sql.gz | tail -n +31 | xargs -r rm --
