# Multi-Vertical News Platform

One codebase, one data pipeline, one React frontend — deployed as multiple independent news sites ("verticals"), each with its own feeds, branding, and Cloudflare Pages project.

| Vertical | Domain focus | Extra features |
|---|---|---|
| `k5` | Security / threat intelligence | Trends dashboard, threat actors, daily briefing |
| `4u` | AI / ML | Daily briefing (generated; page hidden until reviewed) |
| `economics` | Economy (disabled from schedule) | — |
| `storage` | Storage tech (disabled from schedule) | — |
| `finnish` | Finnish news | Duplicates (media-consortium clustering) |

## Layout

```
core/
├── code/
│   ├── base/          # Shared pipeline: merge_feeds, fetch_news, archive_news, news_fetcher/, archiver/
│   ├── <vertical>/    # Per-vertical overrides: smart_groups.py; k5 also has trends + daily report
│   ├── run_pipeline.sh
│   └── sync_web_data.sh
├── source/<vertical>/ # OPML feed definitions
├── data/<vertical>/   # Generated JSON (committed — persistence for incremental archiver)
└── web/               # Shared React SPA, parameterized by VITE_VERTICAL
```

## Running a vertical locally

```bash
# Pipeline (Python 3.11+)
pip install -r core/code/base/requirements.txt
VERTICAL=finnish bash core/code/run_pipeline.sh

# Web app
cd core/web
npm ci
VITE_VERTICAL=finnish npm run build   # prebuild syncs core/data/finnish → public/data/finnish
npm run preview
```

`VITE_VERTICAL` selects branding, nav, feature flags, and the data path (see
`core/web/src/config/verticals.ts`). Dev server: put `VITE_VERTICAL=<v>` in
`core/web/.env.local` and run `npm run dev` (run the sync script once first).

## Adding a new vertical

1. `core/source/<name>/` — OPML feed files (`news.xml`, `blog.xml`, …).
2. `core/code/<name>/smart_groups.py` — classification rules (optional; base defaults used otherwise).
3. Add an entry to `core/web/src/config/verticals.ts`.
4. Add the name to the vertical list in `.github/workflows/update_news_json.yml`.
5. Create a git-integrated Cloudflare Pages project for it (settings in
   `core/web/CLOUDFLARE_DEPLOY.md`).

## Deployment

GitHub Actions (`.github/workflows/update_news_json.yml`) runs the pipeline every
8 hours for the active verticals and commits `core/data/`; each vertical's
git-integrated Cloudflare Pages project rebuilds from that push.
See `core/web/CLOUDFLARE_DEPLOY.md` for per-project build settings.

## Daily briefing (local LLM)

`core/code/base/daily_briefing.py --vertical <v> [--date YYYY-MM-DD]` writes
`core/data/<v>/archive/daily_report_<date>.json` (and `daily_report_latest.json`,
which the `/morning-call` page reads) from that UTC day's archived items. It
map-reduces the items in chunks sized for a 32k-context lane, and every bullet
links to an input item; citations the model invents are dropped. Re-running a
day replaces it. If the endpoint is down it exits 0 and changes nothing.

The LLM is any OpenAI-compatible endpoint (`core/code/base/llm_client.py`):
`LLM_BASE_URL` (default `http://127.0.0.1:11434/v1`), `LLM_MODEL` (default
`qwen38-27b-mtp2:latest`), optional `LLM_API_KEY` (e.g. for
`https://api.openai.com/v1`).

GitHub-hosted runners cannot reach the local lane, so the daily is built on the
host by `core/code/run_daily_briefings.sh` (k5 and 4u). It runs in a dedicated
clone, commits with `[skip ci]` so Cloudflare does not rebuild for it, and goes
live with the next 8-hourly data build. Schedule it with the user units in
`core/code/systemd/`: `bash core/code/systemd/install_daily_timer.sh [--start]`
installs and enables `news-daily-briefing.timer` (01:30 UTC). The service clones
`~/.cache/news-daily/news` on first start and runs that clone's job script, never
a working checkout. Logs: `journalctl --user -u news-daily-briefing` or
`core/code/systemd/daily_status.sh`; `core/code/systemd/check_served_daily.py`
shows which daily k5.ai and 4u.ai serve.
`DAILY_BRIEFING=1 run_pipeline.sh` also runs it after the archive step.

## Daily topics (local LLM)

`core/code/base/build_topics.py --vertical <v> [--date YYYY-MM-DD]` groups that
UTC day's stories into ranked topics and writes
`core/data/<v>/archive/news/topics/<date>.json` (and `topics_latest.json`, which
the `/topics` "Today's topics" page reads). The story rules
(`news_fetcher/stories.py`) pre-cluster first; the LLM only merges, splits and
names those candidates, in batches sized for a 32k lane, and on big days only
stories with a plausibly related partner are sent. Topics are ranked in Python
(distinct sources, story count, recency); every story is in exactly one topic.
If the lane is down or answers badly, the rule clusters are written instead
(`mode: "rules"`), but a day's LLM-built file is never replaced by a
rules-only one. Re-running an unchanged day is a no-op (`--force` rebuilds);
`--rules-only` skips the LLM. Switch a vertical off in `TOPIC_VERTICALS` in
that file.

`run_daily_briefings.sh` builds topics for every vertical in `TOPIC_VERTICALS`
(default all five) before the briefings and commits them the same way. When the
day's topics exist, the briefing uses them as its sections.

Tests: `python3 -m unittest discover -s core/code/base/tests`; web:
`cd core/web && npm test`

## License

AGPL-3.0 — see [LICENSE](LICENSE).
