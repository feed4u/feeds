# Decisions

## 2026-08-23 — GDELT pipelines are retired; 4u.ai (and variants like k5.ai) are the product

**Decision:** We do not run or revive the GDELT-based 4u pipelines for now. The product
is the core-vertical platform behind **4u.ai** and its variants (e.g. **k5.ai** for
security), fed by this repo's `core/` pipeline and the "Update News Feed" GitHub
Actions workflow.

**What this covers:**

- The legacy standalone at `/mnt/data2/projects/4u/4u` (GDELT `4u.py` +
  `deploy_4u.py` + Cloudflare webhook). Its cron lines stay commented out and it is
  not deployed anywhere. A `DEPRECATED.md` in that checkout records the details.
  Note: it was *technically* fixed on 2026-08-21 (venv rebuilt with python3.12,
  `maxrecords` 500→250 after GDELT lowered its cap) — so if it is ever wanted
  again, the pipeline itself works; only the deploy path is gone, because the
  `perttu/4u` GitHub repo was repurposed for the new system.
- The in-repo `4u/` directory (same GDELT approach) and `readd/old/` GDELT
  experiments: kept for reference, not part of the product.

**Why:** The old GDELT site (4u.pages.dev) had been frozen since mid-2025, its
deploy target repo now hosts the new system, and GDELT itself broke the fetch
silently (HTTP 200 with the body "A maximum of 250 records can be returned.").
Meanwhile 4u.ai updates on an intentional 8-hour cadence from `feed4u/feeds` and is
the experience users actually see.

**Guiding principle:** customer experience first — start from what the reader
should experience on 4u.ai / k5.ai and work backwards to the technology, rather
than keeping pipelines alive because they exist.
