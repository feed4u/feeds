# Repository Guidelines

## Project Structure & Module Organization
- `4u/`: shared ingestion code and ops. Primary Python pipeline in `4u/code/base/` (fetch, archive, category metadata) with K5 extras in `4u/code/k5/`. Demo SPA lives in `4u/web/`. Feeds for this vertical are in `4u/source/4u/feeds.xml`.
- `k5-security-news/`, `core/`, `economic-4u/`, `economic/`: vertical apps and dashboards (Vite + React). Each folder contains its own `README.md` and, in many cases, an `AGENTS.md` tailored to that subproject.
- Root utilities: helper scripts like `reorganize_*.py` adjust feed/group metadata across 4u assets.

## Build, Test, and Development Commands
- Pipeline (Python):
  - `cd 4u/code/base && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
  - `python fetch_news.py && python archive_news.py && python build_category_metadata.py`
  - Trends and brief (optional): `cd ../k5 && python create_trends.py`; `OPENAI_API_KEY=... python build_daily_report.py`
- Sync data to a web app: `cd 4u/code && VERTICAL=4u ./sync_web_data.sh` (copies `4u/data/4u/` → `4u/web/public/data/4u/`).
- Frontend (Vite + React): `cd core && npm install && npm run dev` (similarly for `economic-4u/`, `economic/`, or `k5-security-news/web`). Use `npm run build && npm run preview` to validate production.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, `snake_case`. Add type hints for anything serialized to JSON. Keep constants at module top and prefer `pathlib.Path` for filesystem work. Keep Smart Group logic declarative.
- Web (TS/React): PascalCase component and file names under `src/components` and `src/pages`. Utility wrappers under `src/components/ui` follow library naming. Use Tailwind utilities. Lint/format via each app’s `eslint.config.js`.

## Testing Guidelines
- Pipelines: aim for deterministic runs. After the trio, inspect `data/archive/feed_errors_latest.json` and sample `data/news_recent.json` with `jq`. Re-run until stable.
- UI: `npm run lint`, then `npm run build && npm run preview`; manually tour `/`, `/archive`, `/trends`, and any vertical-specific routes.

## Commit & Pull Request Guidelines
- Commits: short, present-tense, imperative (e.g., `trim feed errors`). One dataset or page per commit. Only commit `data/` artifacts when they clarify a change; keep `public/data/` in sync.
- PRs: describe the vertical(s) touched, list any committed JSON outputs, link issues, and include screenshots/GIFs for UI updates.

## Security & Configuration Tips
- Never commit secrets (`OPENAI_API_KEY`, feed creds) or `.env*`. Preserve taxonomy strings in feed definitions (e.g., `4u/source/4u/feeds.xml`) as exact matches are required. For reproducible environments, use Docker in `4u/docker/` and mount only `data/` as writable.
