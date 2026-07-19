# core — Multi-Vertical News Platform

Shared pipeline, per-vertical config, and the parameterized React SPA for all
news verticals (k5, 4u, economics, storage, finnish).

See the repository root `README.md` for layout, local usage, and how to add a
vertical, and `web/CLOUDFLARE_DEPLOY.md` for deployment.

Quick reference:

```bash
# Run the pipeline for one vertical
VERTICAL=k5 bash code/run_pipeline.sh

# Build one web variant
cd web && VITE_VERTICAL=k5 npm run build
```
