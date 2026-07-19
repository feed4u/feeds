# Multi-Vertical News Platform

One codebase, one data pipeline, one React frontend — deployed as multiple independent news sites ("verticals"), each with its own feeds, branding, and Cloudflare Pages project.

| Vertical | Domain focus | Extra features |
|---|---|---|
| `k5` | Security / threat intelligence | Trends dashboard, threat actors, daily SOC briefing |
| `4u` | AI / ML | — |
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

## License

AGPL-3.0 — see [LICENSE](LICENSE).
