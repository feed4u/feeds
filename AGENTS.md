<!-- owner-model:generated — do not edit. The shared rules come from the owner
     model; put anything specific to this repository in AGENTS.local.md
     and it is preserved across updates. -->

# Working agreements

- NOTES.md is this project's working memory. Capture tasks under `## Now`,
  open questions under `## Questions`. Items under `## For me` are reserved
  for the owner — never execute them.
- State what you verified and how. Unrun code is "unverified", not "works".
- The project's purpose and constraints live in the console's Project
  context — read it before large changes.
- Do not prefix a command with environment variables (`FOO=1 python3 x.py`).
  Permission rules match the start of the command, so the prefix hides the
  real one and an allowed command is refused. Take configuration as a CLI
  flag or read it from a file instead.

## Finishing a request

A request is delivered when the whole thing works end to end, not when each
part exists. This is where AI-assisted work fails: features get built,
individually plausible and individually tested, while the request they came
from is never exercised from one end to the other. Half of a request is not
progress on it.

Before reporting a request done:

- Walk the user's path yourself, in the running system, start to finish — the
  same steps the user described, not a unit test standing in for them.
- Exercise the branches that should fail, not only the happy one. A rule that
  is never refused is a rule that was never applied.
- Check the state actually persisted: reload, re-read the file, re-fetch the
  API. Written is not saved, and saved is not round-tripped.
- Verify the state you built for is reachable. A feature guarding a condition
  the system cannot enter is dead code that reviews as complete.
- If part of it cannot be finished, say which part and why, in the same
  message. Do not hand back a half-built request as if it were whole, and do
  not ask permission for the remaining half instead of doing it.

## Long-running work

A command that may run for more than a few minutes must not be run inline. The
session that started it will end — you will be compacted, the chat will close,
the ssh connection will drop — and the work dies with it, silently, with no
record that it was ever started.

Hand it to the runner instead, then end your turn:

    python3 /mnt/data1/projects/owner-model/job_runner.py start \
        --name "arabia harvest" --project arabia --cwd "$PWD" -- <command>

It returns immediately. The job outlives this session, reports itself into the
owner's attention inbox while it runs, and reports again when it finishes or
fails. A run whose process disappears is reported as lost rather than staying
"running" forever.

Build the flow yourself — the runner has no job definitions and needs none.
Write whatever script the work requires, and give it this exit contract so the
runner can drive it one chunk at a time:

    exit 0  -> finished, nothing left to do
    exit 3  -> did one chunk, call me again
    other   -> failed, stop and report

Chunks matter for anything long: each one is a place to resume from, so an
interrupted job keeps its progress instead of starting over. A command with no
chunking still works — it just runs once.

Say in your reply that the job was started and that its result will arrive in
the inbox. Do not poll it, and do not keep the session alive waiting for it.

# Repository Guidelines

This repository (`feed4u/feeds`) is a multi-vertical news platform: one Python
pipeline and one React SPA, both under `core/`, deployed as separate sites
("verticals"). The product is **4u.ai** and variants such as **k5.ai**; the
GDELT-based pipelines are retired (see `DECISIONS.md`, 2026-08-23). `README.md`
has the vertical table and the steps for adding a new vertical.

Run every command below from the repository root unless it says otherwise.

## Project Structure & Module Organization
- `core/code/base/`: shared pipeline. Entry points are `build_category_metadata.py`, `merge_feeds.py`, `fetch_news.py`, `archive_news.py`, `build_topics.py`, `daily_briefing.py`, `convert_feeds_txt.py` and `remove_errored_feeds.py`. Packages: `news_fetcher/` (RSS ingestion, HTML sanitizing, smart groups) and `archiver/`. Also `path_utils.py` (path resolution), `llm_client.py` (OpenAI-compatible client) and `tests/`.
- `core/code/<vertical>/`: per-vertical overrides, mostly `smart_groups.py`. `core/code/k5/` also has `create_trends.py` with `trends_analyzer/`, and `build_daily_report.py`, a k5 wrapper around `daily_briefing.py`.
- `core/code/run_pipeline.sh`, `core/code/sync_web_data.sh`, `core/code/run_daily_briefings.sh`, `core/code/systemd/`: orchestration (see Deployment).
- `core/source/<vertical>/`: OPML feed sections (`news.xml`, `blog.xml` or `blogs.xml`, `podcasts.xml`, `videos.xml`, plus vertical-specific ones such as `viranomaiset.xml`) and the merged `feeds.xml`. `core/source/4u/feeds.txt` is a plain-text feed list.
- `core/data/<vertical>/`: generated JSON. It is committed, because the incremental archiver reads it back.
- `core/web/`: the shared React SPA (React 18, TypeScript, Vite, Tailwind, shadcn-ui, React Router, React Query, Recharts, Vitest). `VITE_VERTICAL` selects branding, nav, feature flags and the data path (`core/web/src/config/verticals.ts`). Routes are in `core/web/src/App.tsx`.
- Verticals: `k5` (security, has trends), `4u` (AI/ML), `finnish`, `economics`, `storage`.
- `core/AGENTS.md` and `core/CLAUDE.md` describe an older standalone layout (`scripts/`, `source/feeds.xml`) that is no longer in the tree. Where they disagree with this file, this file is right. `core/docker/docker-compose.yml` also still calls `/app/scripts/*.py`, so do not rely on the Docker setup without fixing it first.

## Configuration
- Every `core/code/base/*.py` entry point accepts `--vertical`, `--base-dir`, `--data-dir`, `--opml-path`, `--output-path` and `--archive-dir` (`add_path_cli_arguments` in `path_utils.py`). `--base-dir` defaults to the auto-detected `core/`. Pass `--vertical` as a flag. Do not use an environment prefix.
- The fallbacks, used when no flag is given: `VERTICAL` / `K5_VERTICAL`, `K5_BASE_DIR`, `K5_DATA_DIR`, `K5_SOURCE_DIR`, `K5_OPML_PATH`, `K5_OUTPUT_PATH`, `K5_ARCHIVE_DIR`.
- Fetcher tuning is environment-only (`core/code/base/news_fetcher/config.py`): `DAYS_BACK` (default 30), `MAX_WORKERS` (10), `REQUEST_TIMEOUT` (25 s).
- LLM steps (topics, daily briefing) use `llm_client.py`: `LLM_BASE_URL` (default: the local lane `http://127.0.0.1:11434/v1`), `LLM_MODEL`, `LLM_API_KEY` (falls back to `OPENAI_API_KEY`), `LLM_TIMEOUT`, `LLM_RETRIES`. When the endpoint is unreachable, these steps skip without changing files.
- `core/code/run_pipeline.sh` and `core/code/sync_web_data.sh` read the vertical **only** from `VERTICAL` (default `k5`) and have no flag. Run the per-step commands below for another vertical.
- Frontend: copy `core/web/.env.example` to `core/web/.env.local` and set `VITE_VERTICAL=<vertical>`. `VITE_DATA_BASE_PATH` is an optional override; it defaults to `/data/<vertical>`.

## Build, Test, and Development Commands
- Pipeline setup: `python3 -m venv venv && . venv/bin/activate && pip install -r core/code/base/requirements.txt`.
- Pipeline for one vertical, in the order `run_pipeline.sh` uses:
  - `python3 core/code/base/build_category_metadata.py --vertical k5`
  - `python3 core/code/base/merge_feeds.py --vertical k5`
  - `python3 core/code/base/fetch_news.py --vertical k5`. This needs network access and can be long; hand it to the job runner.
  - `python3 core/code/base/archive_news.py --vertical k5`
  - k5 only: `python3 core/code/k5/create_trends.py --vertical k5`
  - Sync to the web app: `bash core/code/sync_web_data.sh` (k5 only, see Configuration). It copies `core/data/<v>/` to `core/web/public/data/<v>/`, excluding `news_recent.json`, `feed_errors_*.json` and `promo_filtered_*.json`.
  - All steps for k5: `bash core/code/run_pipeline.sh`.
- Daily briefing, for a host that can reach the LLM lane: `python3 core/code/base/daily_briefing.py --vertical k5 [--date YYYY-MM-DD]`.
- Python tests: `python3 -m unittest discover -s core/code/base/tests -v`.
- Web app, from `core/web/`: `npm ci`, then `npm run dev`. Sync the data once first, because the dev server does not. Also `npm run lint`, `npm run test` (Vitest), `npm run build` and `npm run preview`. `npm run build` runs `prebuild`, which wipes `public/data` and syncs from the shell variable `VITE_VERTICAL` (default `k5`). It does not read `.env.local`. When building a vertical other than k5, check that the synced data matches the vertical the app is built for.

## Editing Feeds
- Edit the section files in `core/source/<vertical>/`, then rebuild `feeds.xml` with `python3 core/code/base/merge_feeds.py --vertical <vertical>`. The pipeline also re-merges on every run, and the scheduled workflow commits `core/source/`.
- `merge_feeds.py` merges `news blogs podcasts videos` by default, and `--sections` overrides that. For k5 and 4u, whose file is `blog.xml`, it prints `Section missing: …/blogs.xml`; the committed `feeds.xml` is built that same way.
- 4u's plain-text list: `python3 core/code/base/convert_feeds_txt.py --vertical 4u` writes `news.xml`, `blogs.xml`, `podcasts.xml` and `videos.xml` straight into `core/source/4u/`, so no copy step is needed. Then merge. `feeds.txt` and the committed 4u sections have drifted apart, so converting changes the live feed set. Diff before committing.
- Keep taxonomy strings (category names in feed definitions) exact. `build_category_metadata.py` derives category slugs and labels from them.

## Data Files
- `core/data/<v>/news_recent.json`: `generated_at`, `days_back`, `feed_types`, `total_items`, `items[]`. Each item has `title`, `summary`, `summary_html`, `link`, `source`, `type`, `type_label`, `feed_type`, `published`, `published_ts`, `smart_groups`, `curated`. It is a pipeline intermediate that the web app never loads, and sync excludes it because it can exceed Cloudflare Pages' 25 MiB per-file limit.
- `latest.json` (24 h window for the first load), `index.json` (chunk manifest), `archive/` (daily/monthly/yearly, topics, daily reports).
- `category_metadata.json`: `generated_at`, `source`, `total_categories`, `slug_to_label`, `categories[]` (`id`, `label`, `slug`), plus `feed_types` and `hierarchy` when section files exist.
- `trends.json` (k5 only): `summary` (`risk_score`, `risk_level`, `total_articles`, `critical_alerts`, `trending_threats`, `total_cves`, `exploited_cves`, `time_range_days`), `threat_actors`, `cve_analysis`, `attack_surface`, `threat_intelligence`, `insights`, `comparisons`, `windows`.

## Deployment
- `.github/workflows/update_news_json.yml` runs every 8 hours (`23 */8 * * *`) for `k5 4u finnish`. `economics` and `storage` run only through manual dispatch. The workflow runs `run_pipeline.sh` per vertical and commits `core/data/` and `core/source/`. That push is the deploy: each vertical is its own git-integrated Cloudflare Pages project (`core/web/CLOUDFLARE_DEPLOY.md`).
- Daily LLM briefings and topics are not built in Actions, because the runner cannot reach the local lane. They are built on the host by `core/code/run_daily_briefings.sh` (systemd timer in `core/code/systemd/`), committed with `[skip ci]`, and published by the next data push.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, `snake_case`. Add type hints for anything serialized to JSON. Keep constants at module top and prefer `pathlib.Path` for filesystem work. Keep Smart Group logic declarative, in `core/code/<vertical>/smart_groups.py`.
- HTML summaries are sanitized with BeautifulSoup against an allowlist (`news_fetcher/parsers.py`). Keep it an allowlist.
- Web (TS/React): PascalCase component and file names under `src/components` and `src/pages`. Utility wrappers under `src/components/ui` follow library naming. Use Tailwind utilities and lint with `core/web/eslint.config.js`.

## Testing Guidelines
- Pipelines: aim for deterministic runs. After a run, check `core/data/<v>/archive/feed_errors_latest.json` (written locally and not synced) for unexpected failures, and spot-check `core/data/<v>/latest.json` with `jq`.
- UI: `npm run lint`, `npm run test`, then `npm run build && npm run preview`. Tour `/` and `/archive`, plus whichever of `/topics`, `/morning-call`, `/trends`, `/threat-actor(s)/…` and `/duplicates` the vertical's `features` flags in `verticals.ts` turn on.

## Commit & Pull Request Guidelines
- Commits: short, present-tense, imperative (e.g., `trim feed errors`). One dataset or page per commit. Commit generated `core/data/` only when it clarifies a change. `core/web/public/data/` is gitignored, so never commit it.
- PRs: describe the vertical(s) touched, list any committed JSON outputs, link issues, and include screenshots/GIFs for UI updates.

## Security & Configuration Tips
- Never commit secrets (`LLM_API_KEY`, `OPENAI_API_KEY`, feed credentials) or `.env*` files other than `.env.example`.
