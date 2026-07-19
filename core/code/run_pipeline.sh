#!/bin/bash

# K5 Security News - Full Pipeline Execution Script
# This script runs the complete news aggregation pipeline:
# 1. Fetch news from RSS feeds
# 2. Build archives
# 3. Generate trends analytics
# 4. Sync data to web app

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BASE_DIR="$SCRIPT_DIR/base"
VERTICAL="${VERTICAL:-k5}"
COMMON_ARGS=("--vertical" "$VERTICAL")
export K5_BASE_DIR="$PROJECT_ROOT"

DATA_DIR_PATH="$PROJECT_ROOT/data/$VERTICAL"
DATA_DIR_LABEL="data/$VERTICAL"
WEB_DATA_LABEL="web/public/data/$VERTICAL"
export VERTICAL

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Pipeline Execution (${VERTICAL:-default})${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Prepare category metadata and feed manifest
echo -e "${YELLOW}[0/5] Building category metadata...${NC}"
if [ -f "$BASE_DIR/build_category_metadata.py" ]; then
    python "$BASE_DIR/build_category_metadata.py" "${COMMON_ARGS[@]}"
else
    echo -e "${YELLOW}build_category_metadata.py not found, skipping category metadata${NC}"
fi

echo -e "${YELLOW}[1/5] Preparing feed manifest...${NC}"
if [ -f "$BASE_DIR/merge_feeds.py" ]; then
    python "$BASE_DIR/merge_feeds.py" "${COMMON_ARGS[@]}"
else
    echo -e "${YELLOW}merge_feeds.py not found, skipping feed merge${NC}"
fi
echo ""

# Step 1: Fetch News
echo -e "${YELLOW}[2/5] Fetching news from RSS feeds...${NC}"
cd "$PROJECT_ROOT"

if [ -f "$BASE_DIR/fetch_news.py" ]; then
    python "$BASE_DIR/fetch_news.py" "${COMMON_ARGS[@]}"
else
    echo -e "${RED}Error: fetch_news.py not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ News fetching completed${NC}"
echo ""

# Step 2: Build Archives
echo -e "${YELLOW}[3/5] Building news archives...${NC}"

if [ -f "$BASE_DIR/archive_news.py" ]; then
    python "$BASE_DIR/archive_news.py" "${COMMON_ARGS[@]}"
else
    echo -e "${RED}Error: archive_news.py not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Archive building completed${NC}"
echo ""

# Step 3: Generate Trends
echo -e "${YELLOW}[4/5] Generating trends analytics...${NC}"

TREND_SCRIPT=""
if [ -n "$VERTICAL" ] && [ -f "$SCRIPT_DIR/$VERTICAL/create_trends.py" ]; then
  TREND_SCRIPT="$SCRIPT_DIR/$VERTICAL/create_trends.py"
elif [ -n "$VERTICAL" ] && [ -f "$SCRIPT_DIR/$VERTICAL/build_trends_json.py" ]; then
  TREND_SCRIPT="$SCRIPT_DIR/$VERTICAL/build_trends_json.py"
fi

if [ -n "$TREND_SCRIPT" ]; then
  python "$TREND_SCRIPT" "${COMMON_ARGS[@]}"
  echo -e "${GREEN}✓ Trends generation completed${NC}"
  echo ""
else
  echo -e "${YELLOW}No trends script found for vertical '${VERTICAL}'. Skipping.${NC}"
  echo ""
fi

# Step 4: Sync to Web App
echo -e "${YELLOW}[5/5] Syncing data to web application...${NC}"

if [ -f "$SCRIPT_DIR/sync_web_data.sh" ]; then
    chmod +x "$SCRIPT_DIR/sync_web_data.sh"
    "$SCRIPT_DIR/sync_web_data.sh"
else
    echo -e "${RED}Error: sync_web_data.sh not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Data sync completed${NC}"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Pipeline completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Generated files:"
echo "  - ${DATA_DIR_LABEL}/news_recent.json (full dataset)"
echo "  - ${DATA_DIR_LABEL}/latest.json (24h rolling window for initial load)"
echo "  - ${DATA_DIR_LABEL}/index.json (chunk manifest)"
echo "  - ${DATA_DIR_LABEL}/trends.json"
echo "  - ${DATA_DIR_LABEL}/archive/ (monthly/yearly/daily archives)"
echo "  - ${WEB_DATA_LABEL}/ (synced for deployment)"
echo ""

# Show statistics
if [ -f "$DATA_DIR_PATH/latest.json" ]; then
    LATEST_ITEMS=$(jq '.total_items' "$DATA_DIR_PATH/latest.json" 2>/dev/null || echo "?")
    TOTAL_ITEMS=$(jq '.total_items' "$DATA_DIR_PATH/news_recent.json" 2>/dev/null || echo "?")
    echo -e "${BLUE}Statistics:${NC}"
    echo "  Total items: $TOTAL_ITEMS"
    echo "  Latest (24h): $LATEST_ITEMS items"
    echo ""
fi

echo -e "${YELLOW}Next steps:${NC}"
echo "  - Review data in web/public/data/"
echo "  - Run 'cd web && npm run build' to build the web app"
echo "  - Deploy to Cloudflare Pages"
echo ""
