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
