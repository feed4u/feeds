#!/bin/bash
# Sync data from root to web/public/data for React app deployment
# Run this after executing build_news_json.py and build_trends_json.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

VERTICAL="${VERTICAL:-k5}"

SOURCE_DATA="$ROOT_DIR/data/$VERTICAL"
TARGET_DATA="$ROOT_DIR/web/public/data/$VERTICAL"

echo "[INFO] Syncing data from $SOURCE_DATA to $TARGET_DATA..."

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DATA"

# Sync entire directory to keep artifacts consistent.
# news_recent.json is a pipeline intermediate the web app never reads — and it
# can exceed Cloudflare Pages' 25 MiB per-file limit, so keep it out of deploys.
rsync -av --delete \
  --exclude 'news_recent.json' \
  --exclude 'feed_errors_*.json' \
  --exclude 'promo_filtered_*.json' \
  "$SOURCE_DATA/" "$TARGET_DATA/"

echo "[INFO] Data sync complete!"
echo "[INFO] Root data size: $(du -sh "$SOURCE_DATA" | cut -f1)"
echo "[INFO] Web data size: $(du -sh "$TARGET_DATA" | cut -f1)"
