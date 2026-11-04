# core/web: shared news frontend

The React SPA (Vite, TypeScript, Tailwind, shadcn-ui) shared by every vertical.
Which vertical it renders is chosen by `VITE_VERTICAL`. Setup, the pipeline and
the vertical table are in the [root README](../../README.md); this page only
covers working inside `core/web`.

Node 22 is pinned by `.nvmrc`.

## Choosing a vertical

Valid values (see [`.env.example`](.env.example)): `k5`, `4u`, `economics`,
`storage`, `finnish`. Branding, nav, feature flags and the data path
(`/data/<vertical>`) come from `src/config/verticals.ts`.

- **Dev server:** copy `.env.example` to `.env.local` and edit `VITE_VERTICAL`.
  `VITE_DATA_BASE_PATH` is an optional override.
- **Build and preview:** `prebuild` reads the shell variable `VITE_VERTICAL`
  (default `k5`), not `.env.local`. Set it on its own line first, e.g.
  `export VITE_VERTICAL=finnish`. Do not put it in front of the command.

## Commands

From `core/web`:

```sh
npm ci                # install from the lockfile
npm run dev           # dev server; reads .env.local. Sync data first (below)
npm run lint          # ESLint
npm run test          # Vitest
export VITE_VERTICAL=finnish
npm run build         # runs prebuild, then vite build
npm run preview       # serve the built dist/
```

`npm run build` runs `prebuild`, which **deletes `public/data`** and re-syncs
that one vertical's data from `core/data/<vertical>` via
`core/code/sync_web_data.sh`. `public/data` is gitignored. The dev server does
not sync, so sync once before `npm run dev`. `sync_web_data.sh` reads only the
shell variable `VERTICAL` and has no flag; see the root README.

From the repository root, `make lint` and `make test` run the Python checks and
then the web ones (ESLint, Vitest). `make` runs `npm ci` in `core/web` first
when `node_modules` is missing or the lockfile changed.

## Offline checks and the live-digest check

Offline, no network beyond `npm ci`: `make lint`, `make test` (Python unittest
suite and Vitest) and `npm run build`.

The optional browser check of the live digest is separate. It needs network
access to the live 4u digest and Playwright with Chromium. From the repository
root:

```sh
npm --prefix core/web ci
cd core/web && npx playwright install chromium
cd ../..
python3 -m unittest discover -s core/web/tests -v
```

Add `-k test_web_suite` to run one check. Missing dependencies or unavailable
live data make it fail; they are not skipped. Details are in the root README.

## Release

Nothing here publishes. The scheduled GitHub Actions workflow
(`.github/workflows/update_news_json.yml`) runs the pipeline and commits
`core/data/`. Each vertical is its own git-integrated Cloudflare Pages project
that rebuilds from that push. Build settings and the project mapping are in
[`CLOUDFLARE_DEPLOY.md`](CLOUDFLARE_DEPLOY.md).
