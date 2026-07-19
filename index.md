# News Projects Overview

This directory is now a single git repository containing the consolidated
multi-vertical news platform under `core/`. One shared Python pipeline and one
React SPA serve five verticals — k5 (security), 4u (AI/ML), economics, storage,
and finnish — each deployed to its own Cloudflare Pages project from the same
codebase. See the root `README.md` for usage and `core/web/CLOUDFLARE_DEPLOY.md`
for deployment.

The consolidation resolved the earlier pain points (documented in previous
revisions of this file): duplicated pipelines, per-vertical repo copies, drift
between frontends, and hardcoded configuration. Verticals are now data + a
config entry, not code copies:

- Feeds: `core/source/<vertical>/*.xml`
- Classification: `core/code/<vertical>/smart_groups.py` (optional)
- Branding/features: one entry in `core/web/src/config/verticals.ts`
- CI: one list in `.github/workflows/update_news_json.yml`

## Legacy directories (on disk, excluded from git)

These predate the consolidation and are kept untouched for reference; they are
listed in `.gitignore` and are not part of the repository:

- `k5-security-news/` — original standalone security aggregator (own git repo)
- `4u/` — original GDELT-based AI news aggregator
- `finnish/` — standalone fork the finnish vertical was migrated from
- `economic/`, `storage/` — disconnected Lovable-generated frontends
- `economic-4u/`, `storage-4u/` — cloned full-stack pipeline copies
- `readd/`, `source/` — experimental / leftover copies
