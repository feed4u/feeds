#!/bin/bash
# Daily LLM briefings, built on this host (the GitHub-hosted runner cannot reach
# the local LLM lane) and pushed to GitHub.
#
# Runs in its own dedicated clone so it never touches a working checkout:
#   1. clone (first run) or hard-reset the clone to origin/main
#   2. build yesterday's (UTC) topics for each vertical in TOPIC_VERTICALS
#      (build_topics.py; a vertical switched off in its TOPIC_VERTICALS dict
#      is skipped) and the daily for each vertical in DAILY_VERTICALS — topics
#      first, so the daily uses them as its sections
#   3. commit the daily_report_*.json and news/topics/*.json files with
#      "[skip ci]" so Cloudflare Pages does not rebuild for it — the next
#      8-hourly data push publishes it
#   4. push (rebasing over a concurrent data push if needed)
#
# A vertical whose LLM call is unavailable is skipped without changing files
# (topics fall back to the rule-based grouping unless an LLM-built file for
# the day already exists); if nothing changed, nothing is committed.
#
# Usage: core/code/run_daily_briefings.sh [--no-push] [--date YYYY-MM-DD]
#          [--branch BRANCH] [--clone DIR] [--verticals "k5 4u"]
#          [--topic-verticals "k5 4u finnish economics storage"]
# --branch builds from (and pushes to) another branch, e.g. to try the job on
# a PR branch before merge; --clone, --verticals and --topic-verticals
# override the settings below.
# Config (environment, optional):
#   NEWS_DAILY_CLONE   clone path (default ~/.cache/news-daily/news)
#   NEWS_DAILY_REMOTE  git remote URL (default: origin of the repo holding this script)
#   DAILY_VERTICALS    default "k5 4u"
#   TOPIC_VERTICALS    default "k5 4u finnish economics storage"
#   LLM_BASE_URL / LLM_MODEL / LLM_API_KEY  see core/code/base/llm_client.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLONE_DIR="${NEWS_DAILY_CLONE:-$HOME/.cache/news-daily/news}"
REMOTE="${NEWS_DAILY_REMOTE:-$(git -C "$SCRIPT_DIR" remote get-url origin)}"
VERTICALS="${DAILY_VERTICALS:-k5 4u}"
TOPIC_VERTICALS_LIST="${TOPIC_VERTICALS:-k5 4u finnish economics storage}"
BRANCH=main
PUSH=1
DATE_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --no-push) PUSH=0 ;;
    --date) DATE_ARGS=(--date "$2"); shift ;;
    --branch) BRANCH="$2"; shift ;;
    --clone) CLONE_DIR="$2"; shift ;;
    --verticals) VERTICALS="$2"; shift ;;
    --topic-verticals) TOPIC_VERTICALS_LIST="$2"; shift ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
  shift
done

if [ ! -d "$CLONE_DIR/.git" ]; then
  mkdir -p "$(dirname "$CLONE_DIR")"
  git clone --depth 1 --branch "$BRANCH" "$REMOTE" "$CLONE_DIR"
fi
cd "$CLONE_DIR"
# FETCH_HEAD, not origin/$BRANCH: a single-branch clone only tracks the branch
# it was cloned with, so origin/<other> would not exist.
git fetch --depth 1 origin "$BRANCH"
git reset --hard FETCH_HEAD
git clean -fdq

in_list() { case " $2 " in *" $1 "*) return 0 ;; esac; return 1; }

STARTED=$(date +%s)
# Topics first, so each briefing can use its day's topics as sections.
for V in $(printf '%s\n' $TOPIC_VERTICALS_LIST $VERTICALS | awk '!seen[$0]++'); do
  if in_list "$V" "$TOPIC_VERTICALS_LIST"; then
    echo "== topics: $V"
    python3 core/code/base/build_topics.py --vertical "$V" "${DATE_ARGS[@]}"
  fi
  if in_list "$V" "$VERTICALS"; then
    echo "== daily briefing: $V"
    python3 core/code/base/daily_briefing.py --vertical "$V" "${DATE_ARGS[@]}"
  fi
done
echo "== topics and briefings took $(( $(date +%s) - STARTED ))s"

git add core/data/*/archive/daily_report_*.json
git add core/data/*/archive/news/topics/*.json 2>/dev/null || true
if git diff --cached --quiet; then
  echo "No daily changes to commit"
  exit 0
fi

git -c user.name="news-daily (host)" -c user.email="news-daily@localhost" \
  commit -q -m "Update daily briefings ($VERTICALS) [skip ci]"
git log -1 --stat --format='committed %h: %s'

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
  git rebase FETCH_HEAD
done
echo "push failed after 3 attempts" >&2
exit 1
