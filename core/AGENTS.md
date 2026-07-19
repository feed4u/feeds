# Repository Guidelines

## Project Structure & Module Organization
- `scripts/`: pipeline entry points (`fetch_news.py`, `archive_news.py`, `create_trends.py`, `build_category_metadata.py`) and helpers (`news_fetcher`, `trends_analyzer`, `archiver`, `config`).
- `source/feeds.xml`: source feeds and taxonomy strings (match names exactly).
- `data/`: generated datasets; mirror required files into `web/public/data/`.
- `web/`: React app — routes in `src/pages/`, shared UI in `src/components/`.
- `docs/`, `docker/`: reference notes and container workflows.

## Build, Test, and Development Commands
- `python -m venv venv && source venv/bin/activate && pip install -r scripts/requirements.txt` — provision pipeline deps.
- `python scripts/build_category_metadata.py` — rebuild `data/category_metadata.json` when taxonomy changes.
- `python scripts/fetch_news.py && python scripts/archive_news.py && python scripts/create_trends.py` — ingestion → archive → trends. Env: `DAYS_BACK`, `MAX_WORKERS`, `SKIP_ARCHIVE`.
- `./scripts/run_pipeline.sh` — orchestrates pipeline and copies `data/` → `web/public/data/`.
- `cd web && npm install && npm run dev && npm run lint && npm run build && npm run preview` — install, develop, lint, build, preview.

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, `snake_case` APIs, type hints for anything serialized to JSON. Define constants at module top; use `pathlib.Path` for filesystem.
- Web: PascalCase components stored in `kebab-case.tsx` files (e.g., `src/components/chart-card.tsx` exports `ChartCard`). Use Tailwind utilities. ESLint/Prettier via `web/eslint.config.js`.
- Describe Smart Groups declaratively; avoid ad‑hoc logic.

## Testing Guidelines
- Target deterministic runs. After the trio (or `run_pipeline.sh`), verify `data/archive/feed_errors_latest.json` only has expected failures. Spot‑check `data/news_recent.json` with `jq`.
- UI: sync datasets, `npm run lint`, `npm run build && npm run preview`, then tour `/`, `/archive`, `/trends`, `/morning-call`.

## Commit & Pull Request Guidelines
- Commits: short, present‑tense, imperative (e.g., `trim feed errors`). One dataset or page per commit.
- PRs: summarize touched datasets, list committed JSON artifacts, link issues, include screenshots/GIFs for UI updates, and note follow‑up workflows (Cloudflare Pages, SOC briefings) to rerun.

## Security & Configuration Tips
- Never commit `OPENAI_API_KEY`, feed credentials, or `.env` files. Preserve taxonomy strings in `source/feeds.xml` and Smart Group configs. Only commit regenerated `data/` when it clarifies a change, and run `scripts/sync_web_data.sh` so `web/public/data/` stays in sync. Docker runs should mount `data/` as the sole writable path.

