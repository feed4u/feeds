#!/bin/bash

# K5 Security News - Full Pipeline with Daily Report
# This script runs the complete pipeline including optional daily report generation

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

DATA_DIR_LABEL="data/$VERTICAL"
WEB_DATA_LABEL="web/public/data/$VERTICAL"
export VERTICAL

# Parse arguments
INCLUDE_REPORT=false
if [[ "$1" == "--with-report" ]]; then
    INCLUDE_REPORT=true
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${RED}Error: OPENAI_API_KEY environment variable not set${NC}"
        echo "Daily report generation requires OpenAI API key"
        echo "Set it with: export OPENAI_API_KEY='your-key-here'"
        exit 1
    fi
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Full Pipeline (${VERTICAL:-default})${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Prepare feed manifest
echo -e "${YELLOW}[0/5] Preparing feed manifest...${NC}"
if [ -f "$BASE_DIR/merge_feeds.py" ]; then
    python "$BASE_DIR/merge_feeds.py" "${COMMON_ARGS[@]}"
else
    echo -e "${YELLOW}merge_feeds.py not found, skipping feed merge${NC}"
fi
echo ""

# Step 1: Fetch News
echo -e "${YELLOW}[1/5] Fetching news from RSS feeds...${NC}"
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
echo -e "${YELLOW}[2/5] Building news archives...${NC}"

if [ -f "$BASE_DIR/archive_news.py" ]; then
    python "$BASE_DIR/archive_news.py" "${COMMON_ARGS[@]}"
else
    echo -e "${RED}Error: archive_news.py not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Archive building completed${NC}"
echo ""

# Step 3: Generate Trends
echo -e "${YELLOW}[3/5] Generating trends analytics...${NC}"

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

# Step 4: Daily Report (Optional)
if [ "$INCLUDE_REPORT" = true ]; then
    echo -e "${YELLOW}[4/5] Generating daily report (LLM-powered)...${NC}"

    REPORT_SCRIPT="$SCRIPT_DIR/$VERTICAL/build_daily_report.py"
    if [ -f "$REPORT_SCRIPT" ]; then
        python "$REPORT_SCRIPT" "${COMMON_ARGS[@]}"
        echo -e "${GREEN}✓ Daily report generated${NC}"
    else
        echo -e "${YELLOW}⚠ build_daily_report.py not found for ${VERTICAL}, skipping...${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}[4/5] Daily report generation skipped${NC}"
    echo -e "     Use --with-report flag to include daily report"
    echo ""
fi

# Step 5: Sync to Web App
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
if [ "$INCLUDE_REPORT" = true ]; then
    echo "  - ${DATA_DIR_LABEL}/archive/daily_report_latest.json"
fi
echo "  - ${WEB_DATA_LABEL}/ (synced for deployment)"
echo ""

# Show data statistics
DATA_DIR_PATH="$PROJECT_ROOT/data/$VERTICAL"
if [ -f "$DATA_DIR_PATH/latest.json" ]; then
    LATEST_ITEMS=$(jq '.total_items' "$DATA_DIR_PATH/latest.json" 2>/dev/null || echo "?")
    TOTAL_ITEMS=$(jq '.total_items' "$DATA_DIR_PATH/news_recent.json" 2>/dev/null || echo "?")
    echo -e "${BLUE}Statistics:${NC}"
    echo "  Total items: $TOTAL_ITEMS"
    echo "  Latest (24h): $LATEST_ITEMS items"
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review data in web/public/data/"
echo "  2. Build web app: cd web && npm run build"
echo "  3. Deploy to Cloudflare Pages"
echo ""
