#!/usr/bin/env bash
set -e

BACKUP_DIR="./backups/mongo"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUT_DIR="$BACKUP_DIR/mei_mongo_$TIMESTAMP"

docker exec mongo mongodump --out "$OUT_DIR"

echo "Backup Mongo gerado em $OUT_DIR"
