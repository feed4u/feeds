# Deploying to Cloudflare Pages

Each active vertical deploys from this one repo (`github.com/feed4u/feeds`) to its
own **git-integrated** Cloudflare Pages project. Cloudflare builds the variant on
every push to `main`; GitHub Actions (`.github/workflows/update_news_json.yml`)
runs the data pipeline every 8 hours and pushes the data commit, which is what
triggers the deploys.

## Per-project build configuration

Create/convert each Pages project (dashboard → Workers & Pages → project →
Settings, or "Connect to Git" for new ones) with:

| Setting | Value |
|---|---|
| Production branch | `main` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `core/web` |
| Environment variables | `VITE_VERTICAL=<vertical>` (and remove/set `NODE_VERSION=22`; `core/web/.nvmrc` already pins 22) |
| Build watch paths (include) | `core/web/*`, `core/data/<vertical>/*` |

Current project mapping:

| Vertical | Pages project |
|---|---|
| k5 | `5k-security-news` |
| 4u | `4u-ml` |
| economics | `economic-4u` (vertical disabled from the schedule) |
| storage | *(create when needed)* |
| finnish | *(create when needed)* |

`VITE_VERTICAL` selects branding, meta tags, nav/feature flags, and the data path
(`/data/<vertical>`) from `core/web/src/config/verticals.ts`. The `prebuild`
script wipes `public/data/` and copies only that vertical's data from
`core/data/<vertical>`, excluding `news_recent.json` and error reports (the web
app never reads them, and `news_recent.json` can exceed Cloudflare's 25 MiB
per-file limit). Pages serves SPA fallback natively (no `_redirects` needed;
Cloudflare flags the classic `/* /index.html 200` rule as an infinite loop).

## Build quota

Free plan = 500 Cloudflare builds/month per account, and every push builds every
git-integrated project. The 8-hour cron (~90 pushes/month) × 4 active projects
≈ 360 builds + ~30 from the daily k5 morning-call commit — inside quota. **Set
the build watch paths above** so unrelated commits (docs, other verticals) skip
builds. If you add projects or shorten the cron, redo this math — or switch a
project back to direct upload (`wrangler pages deploy`), which bypasses the
quota but requires the project to NOT be git-connected.

## GitHub secrets

- `OPENAI_API_KEY` — optional, k5 morning-call briefing only.

(No Cloudflare secrets are needed while all deploys are git-integrated.)

## Manual local build of one vertical

```bash
cd core/web
npm ci
VITE_VERTICAL=k5 npm run build && npm run preview
```

## Constraints to watch

- **25 MiB per-file limit**: yearly archive JSONs are the biggest deployed files
  (~15 MiB after one partial year). If one crosses 25 MiB, switch the Archive
  page to monthly files or exclude `yearly/` in `core/code/sync_web_data.sh`.
- Repo history grows with the 8-hourly data commits; long-term fix is moving
  data to R2.

## Troubleshooting

- **Build fails with `rsync: command not found`**: shouldn't happen —
  `sync_web_data.sh` falls back to tar on the Pages build image.
- **Site loads but no items**: check the deployed build contains
  `data/<vertical>/latest.json`; re-run the pipeline workflow for that vertical.
- **Deep links 404**: Pages' automatic SPA fallback requires that `dist/` has no
  `404.html`; don't add one.
- **Builds skipped unexpectedly**: check the project's build watch paths include
  `core/data/<vertical>/*`.
