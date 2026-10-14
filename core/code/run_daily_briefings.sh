#!/bin/bash
# Daily LLM briefings, built on this host (the GitHub-hosted runner cannot reach
# the local LLM lane) and pushed to GitHub.
#
# Runs in its own dedicated clone so it never touches a working checkout:
#   1. clone (first run) or hard-reset the clone to origin/main
#   2. build yesterday's (UTC) daily for each vertical in DAILY_VERTICALS
#   3. commit the daily_report_*.json files with "[skip ci]" so Cloudflare Pages
#      does not rebuild for it — the next 8-hourly data push publishes it
#   4. push (rebasing over a concurrent data push if needed)
#
# A vertical whose LLM call is unavailable is skipped without changing files;
# if nothing changed, nothing is committed.
#
# Usage: core/code/run_daily_briefings.sh [--no-push] [--date YYYY-MM-DD]
# Config (environment, optional):
#   NEWS_DAILY_CLONE   clone path (default ~/.cache/news-daily/news)
#   NEWS_DAILY_REMOTE  git remote URL (default: origin of the repo holding this script)
#   DAILY_VERTICALS    default "k5 4u"
#   LLM_BASE_URL / LLM_MODEL / LLM_API_KEY  see core/code/base/llm_client.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLONE_DIR="${NEWS_DAILY_CLONE:-$HOME/.cache/news-daily/news}"
REMOTE="${NEWS_DAILY_REMOTE:-$(git -C "$SCRIPT_DIR" remote get-url origin)}"
VERTICALS="${DAILY_VERTICALS:-k5 4u}"
BRANCH=main
PUSH=1
DATE_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --no-push) PUSH=0 ;;
    --date) DATE_ARGS=(--date "$2"); shift ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
  shift
done

if [ ! -d "$CLONE_DIR/.git" ]; then
  mkdir -p "$(dirname "$CLONE_DIR")"
  git clone --depth 1 --branch "$BRANCH" "$REMOTE" "$CLONE_DIR"
fi
cd "$CLONE_DIR"
git fetch --depth 1 origin "$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fdq

STARTED=$(date +%s)
for V in $VERTICALS; do
  echo "== daily briefing: $V"
  python3 core/code/base/daily_briefing.py --vertical "$V" "${DATE_ARGS[@]}"
done
echo "== briefings took $(( $(date +%s) - STARTED ))s"

git add core/data/*/archive/daily_report_*.json
if git diff --cached --quiet; then
  echo "No daily changes to commit"
  exit 0
fi

git -c user.name="news-daily (host)" -c user.email="news-daily@localhost" \
  commit -q -m "Update daily briefings ($VERTICALS) [skip ci]"

if [ "$PUSH" != "1" ]; then
  echo "--no-push: committed in $CLONE_DIR only"
  exit 0
fi

for attempt in 1 2 3; do
  if git push origin "HEAD:$BRANCH"; then
    exit 0
  fi
  echo "push rejected (attempt $attempt); rebasing over origin/$BRANCH"
  git fetch --depth 50 origin "$BRANCH"
  git rebase "origin/$BRANCH"
done
echo "push failed after 3 attempts" >&2
exit 1
