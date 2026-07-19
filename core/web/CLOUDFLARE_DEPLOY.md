# Deploying to Cloudflare Pages

All five verticals (k5, 4u, economics, storage, finnish) deploy from this one repo,
each to its own Cloudflare Pages project via **direct upload** (`wrangler pages deploy`).
There is no Cloudflare git integration — GitHub Actions builds and deploys hourly,
so direct uploads don't consume the Pages build quota.

## One-time setup

1. **Create the Pages projects** (once per vertical):

   ```bash
   npm install -g wrangler
   wrangler login
   for V in k5 4u economics storage finnish; do
     wrangler pages project create "news-$V" --production-branch=main
   done
   ```

2. **Create a Cloudflare API token** with the *Cloudflare Pages — Edit* permission
   (dash.cloudflare.com → My Profile → API Tokens).

3. **Add GitHub repository secrets**:
   - `CLOUDFLARE_API_TOKEN` — the token from step 2
   - `CLOUDFLARE_ACCOUNT_ID` — from the Cloudflare dashboard sidebar
   - `OPENAI_API_KEY` — optional, for the k5 morning-call briefing

4. Push the repo to GitHub. The `Update News Feed` workflow
   (`.github/workflows/update_news_json.yml`) then runs hourly: pipeline for all
   verticals → commit `core/data/` → build each variant → deploy each to
   `https://news-<vertical>.pages.dev`.

5. **Custom domains** (optional): per project in the Pages dashboard → Custom domains.

## Manual deploy of one vertical

```bash
cd core/web
npm ci
VITE_VERTICAL=finnish npm run build   # prebuild syncs core/data/finnish → public/data/finnish
wrangler pages deploy dist --project-name=news-finnish --branch=main
```

## How a variant build works

- `VITE_VERTICAL` selects the entry in `src/config/verticals.ts`: branding, meta
  tags, nav items, and feature flags (trends/morning-call/threat-actors/duplicates).
- The data path defaults to `/data/<vertical>`; the `prebuild` script wipes
  `public/data/` and rsyncs only that vertical's data from `core/data/<vertical>`,
  excluding `news_recent.json` and error reports (the web app never reads them, and
  `news_recent.json` can exceed Cloudflare's 25 MiB per-file limit).
- `public/_redirects` (`/* /index.html 200`) handles SPA deep links.

## Constraints to watch

- **25 MiB per-file limit**: yearly archive JSONs are the biggest deployed files
  (~15 MiB after one partial year). If one crosses 25 MiB, switch the Archive page
  to monthly files or exclude `yearly/` from `core/code/sync_web_data.sh`.
- Repo history grows with hourly data commits; long-term fix is moving data to R2.

## Troubleshooting

- **Deploy fails**: `wrangler whoami`, check `CLOUDFLARE_API_TOKEN` scope, and
  `wrangler pages project list` for the project name.
- **Site loads but no items**: check `dist/data/<vertical>/latest.json` exists in
  the deployed build; re-run the pipeline for that vertical.
- **Deep links 404**: ensure `public/_redirects` made it into `dist/`.
