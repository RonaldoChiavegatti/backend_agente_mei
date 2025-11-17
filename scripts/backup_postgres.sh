#!/usr/bin/env bash
set -e

BACKUP_DIR="./backups/postgres"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILE="$BACKUP_DIR/mei_postgres_$TIMESTAMP.sql"

docker exec postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -F p > "$FILE"

echo "Backup Postgres gerado em $FILE"
