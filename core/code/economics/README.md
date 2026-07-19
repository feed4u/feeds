Economics Vertical
===================

This vertical aggregates macroeconomic news, research, and podcasts using sources in `source/economics/` and classifies items into economics‑specific Smart Groups.

Run
- VERTICAL=economics code/run_pipeline.sh
- Or: python code/base/fetch_news.py --vertical economics

Feeds
- News: `source/economics/news.xml`
- Blogs/Research: `source/economics/blogs.xml` (also auto‑detected as `blogs`)
- Podcasts: `source/economics/podcasts.xml`

Smart Groups
- Rules live in `code/economics/smart_groups.py` and override defaults. Groups include Macro & Growth, Monetary Policy, Central Banks, Inflation & Prices, Labor & Wages, Fiscal Policy & Debt, Trade & Supply Chains, Energy & Commodities, Markets & Rates, Housing, Financial Stability, Emerging Markets, China/US/Euro Area, Nordics & Finland, and Climate & ESG Economics.

Outputs
- Data is written to `data/economics/` and mirrored to `web/public/data/economics/` by `code/sync_web_data.sh`.

Notes
- The pipeline auto‑detects `blogs.xml` and `podcasts.xml` alongside `news.xml`.
