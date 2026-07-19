# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a multi-project repository containing several news aggregation and intelligence systems focused on AI/ML and security content. The repository follows a modular "vertical" architecture where different content domains (e.g., security, AI/ML) share common infrastructure.

### Project Structure

```
news/
├── core/                    # Shared infrastructure for multi-vertical news aggregation
│   ├── code/base/          # Shared Python modules and utilities
│   ├── source/             # Feed source files organized by vertical
│   ├── data/               # Generated data artifacts per vertical
│   └── web/                # React SPA (shared frontend)
│
├── k5-security-news/       # Legacy standalone security news aggregator
│   ├── scripts/            # Python data pipeline (news_fetcher, archiver, trends_analyzer)
│   ├── web/               # React SPA with Vite + TypeScript
│   ├── source/            # OPML feed definitions
│   └── data/              # Generated JSON outputs
│
├── 4u/                     # Standalone AI/ML news aggregator with semantic clustering
│   ├── 4u.py              # Main application script using GDELT API
│   └── front/             # Web interface
│
└── readd/                  # Alternative/experimental implementations
    ├── scripts/           # Python pipeline scripts
    └── venv/              # Python virtual environment
```

## Core Multi-Vertical Architecture

The `core/` directory implements a shared platform for managing multiple content "verticals" (e.g., k5 for security, 4u for AI/ML). This is the primary development focus.

### Key Concepts

- **Vertical**: A content domain (e.g., "k5" for security, "4u" for AI/ML) with its own feeds and data
- **Feed Types**: Each vertical can have news, blogs, podcasts, and videos
- **Smart Groups**: Non-exclusive content classification tags (e.g., "Ransomware", "Vulnerabilities")
- **OPML Format**: RSS feed definitions stored in XML format

### Path Resolution

The shared `path_utils.py` module handles path resolution across verticals:

```python
from core.code.base.path_utils import load_path_config

# Environment variables supported:
# VERTICAL or K5_VERTICAL - which vertical to process
# K5_DATA_DIR - override data directory
# K5_SOURCE_DIR - override source directory
# K5_OPML_PATH - override OPML file path

config = load_path_config(vertical="k5")
# Returns PathConfig with resolved paths for:
# - base_dir, code_dir, data_dir
# - source_dir, opml_path, output_path, archive_dir
```

### Vertical Workflows

**K5 Security Vertical** (see `core/k5.md`):
```bash
# 1. Edit feeds in source/k5/news.xml, blog.xml, podcasts.xml, videos.xml

# 2. Merge sections into feeds.xml
python core/code/base/merge_feeds.py --vertical k5 --base-dir core

# 3. Run pipeline (fetch, archive, sync)
VERTICAL=k5 ./core/code/run_pipeline.sh

# 4. Generate category metadata and sync to web
VERTICAL=k5 python core/code/base/build_category_metadata.py
VERTICAL=k5 core/code/sync_web_data.sh

# 5. Configure frontend
# Set VITE_DATA_BASE_PATH=/data/k5 in core/web/.env.local
cd core/web
npm run dev
```

**4U AI/ML Vertical** (see `core/4u.md`):
```bash
# 1. Edit core/source/4u/feeds.txt (plain text list)

# 2. Convert text to OPML sections
python core/code/base/convert_feeds_txt.py --vertical 4u --base-dir core
mkdir -p source/4u
cp core/source/4u/*.xml source/4u/

# 3. Merge sections
python core/code/base/merge_feeds.py --vertical 4u --base-dir core

# 4. Run pipeline and sync
VERTICAL=4u ./core/code/run_pipeline.sh
VERTICAL=4u python core/code/base/build_category_metadata.py
VERTICAL=4u core/code/sync_web_data.sh

# 5. Configure frontend
# Set VITE_DATA_BASE_PATH=/data/4u in core/web/.env.local
```

## K5 Security News (Legacy Standalone)

Comprehensive security news aggregation platform with threat intelligence analysis. This is a complete, production-ready system documented in `k5-security-news/CLAUDE.md`.

### Quick Commands

```bash
cd k5-security-news

# Development setup
cd web && npm install
python -m venv venv && source venv/bin/activate
pip install -r scripts/requirements.txt

# Run data pipeline
python scripts/fetch_news.py              # Fetch from RSS feeds
python scripts/archive_news.py            # Build archives
python scripts/create_trends.py           # Generate threat intelligence
./scripts/sync_web_data.sh               # Sync to web app

# Or use convenience wrapper
./scripts/run_pipeline.sh                # All-in-one pipeline

# Optional: LLM-powered SOC briefing
python scripts/build_daily_report.py     # Requires OPENAI_API_KEY

# Frontend development
cd web
npm run dev          # http://localhost:5173
npm run build        # Production build
npm run lint         # ESLint
```

### Architecture

**Data Flow**: `source/feeds.xml` → `news_fetcher` → `data/news_recent.json` → `archiver` → `archive/monthly/` + `archive/yearly/` → `trends_analyzer` → `data/trends.json` → `sync_web_data.sh` → `web/public/data/`

**Modular Packages**:
- `news_fetcher` - RSS ingestion, HTML sanitization, smart group classification
- `archiver` - Historical archive generation, deduplication
- `trends_analyzer` - Threat intelligence (attack patterns, CVEs, threat actors, risk scoring)

**Frontend**: React 18 + TypeScript + Vite + shadcn-ui + Tailwind CSS

**Key Files**:
- `source/feeds.xml` - OPML feed definitions (100+ security feeds)
- `data/news_recent.json` - Latest 30 days of articles
- `data/trends.json` - Threat intelligence analytics
- `data/category_metadata.json` - Category mappings

See `k5-security-news/CLAUDE.md` for complete architecture documentation.

## 4U AI News Aggregator

Standalone AI/ML news aggregator using GDELT API with semantic clustering.

### Quick Commands

```bash
cd 4u

# Setup
pip install -r requirements.txt

# Run application
python 4u.py              # Fetch news and generate clusters

# Serve web interface
cd front && python -m http.server 8000
# Visit http://localhost:8000

# Docker
docker-compose up --build
# Or with nginx
docker-compose --profile with-nginx up --build
```

### Architecture

- **Data Source**: GDELT Project API (global news database)
- **Clustering**: TF-IDF vectorization + cosine similarity + Agglomerative Clustering
- **Text Processing**: nltk for lemmatization, BeautifulSoup for parsing
- **Output**: JSON files with grouped articles in `front/links/`

**Search Terms** (configurable in `4u.py`):
- "artificial intelligence"
- "data science"
- "openai"
- "generative ai"
- "deep learning"

## Readd Directory

Contains alternative implementations and experimental code. Scripts mirror the k5-security-news pipeline structure:
- `build_news_json.py` - Feed fetching
- `archive_news.py` - Archive generation
- `create_trends.py` - Threat analysis
- `news_fetcher/`, `archiver/`, `trends_analyzer/` - Modular packages

This appears to be a testing/development area for k5 features.

## Common Development Workflows

### Adding a New RSS Feed

**For k5-security-news standalone**:
1. Edit `k5-security-news/source/feeds.xml` directly
2. Validate: `xmllint --noout k5-security-news/source/feeds.xml`
3. Run pipeline: `cd k5-security-news && ./scripts/run_pipeline.sh`

**For core/k5 vertical**:
1. Edit `source/k5/news.xml`, `source/k5/blog.xml`, etc.
2. Merge: `python core/code/base/merge_feeds.py --vertical k5 --base-dir core`
3. Run pipeline: `VERTICAL=k5 ./core/code/run_pipeline.sh`

**For core/4u vertical**:
1. Edit `core/source/4u/feeds.txt` (plain text)
2. Convert: `python core/code/base/convert_feeds_txt.py --vertical 4u --base-dir core`
3. Merge: `python core/code/base/merge_feeds.py --vertical 4u --base-dir core`
4. Run pipeline: `VERTICAL=4u ./core/code/run_pipeline.sh`

### Testing Changes Locally

**k5-security-news**:
```bash
cd k5-security-news
./scripts/run_pipeline.sh
cd web && npm run dev
# Visit http://localhost:5173
```

**core vertical**:
```bash
VERTICAL=k5 ./core/code/run_pipeline.sh
VERTICAL=k5 core/code/sync_web_data.sh
cd core/web
# Ensure .env.local has VITE_DATA_BASE_PATH=/data/k5
npm run dev
```

### Running Tests

**Python linting** (if configured):
```bash
# From k5-security-news/
python -m pylint scripts/news_fetcher/*.py
```

**Frontend linting**:
```bash
cd k5-security-news/web
npm run lint
```

## Key Technologies

### Python Stack
- `feedparser` - RSS/Atom parsing
- `beautifulsoup4` - HTML sanitization
- `openai` - LLM API (optional, for briefings)
- `requests` - HTTP client
- `scikit-learn` - Clustering (4u project)
- `nltk` - Text processing (4u project)

### JavaScript/TypeScript Stack
- React 18 - UI framework
- Vite - Build tool and dev server
- TypeScript - Type safety
- Tailwind CSS - Styling
- shadcn-ui - Component library
- React Router - Client-side routing
- React Query - Data fetching/caching
- Recharts - Data visualization

## Environment Variables

### Core Vertical System
- `VERTICAL` or `K5_VERTICAL` - Which vertical to process (e.g., "k5", "4u")
- `K5_DATA_DIR` - Override data directory location
- `K5_SOURCE_DIR` - Override source directory location
- `K5_OPML_PATH` - Override OPML file path
- `K5_OUTPUT_PATH` - Override output JSON path
- `K5_ARCHIVE_DIR` - Override archive directory

### K5 Security News
- `OPENAI_API_KEY` - For LLM-powered daily briefings
- `DAYS_BACK` - How many days of news to fetch (default: 30)
- `MAX_WORKERS` - Parallel feed fetching workers (default: 10)
- `REQUEST_TIMEOUT` - HTTP timeout in seconds (default: 25)

### Frontend
- `VITE_DATA_BASE_PATH` - Data path prefix (e.g., "/data/k5", "/data/4u")

## Data Schemas

### news_recent.json
```json
{
  "generated_at": "2024-12-16T14:30:00Z",
  "days_back": 30,
  "total_items": 1245,
  "items": [
    {
      "title": "Article title",
      "summary": "Plain text summary",
      "summary_html": "<p>HTML summary</p>",
      "link": "https://example.com/article",
      "source": "Source name",
      "type": "news|blog|podcast|video",
      "type_label": "News|Blog|Podcast|Video",
      "published": "2024-12-16T10:00:00Z",
      "published_ts": 1734344400,
      "smart_groups": ["Group 1", "Group 2"],
      "curated": true|false
    }
  ]
}
```

### category_metadata.json
```json
{
  "categories": {
    "category_key": "Display Name"
  },
  "generated_at": "2024-12-16T14:00:00Z"
}
```

### trends.json (k5 only)
```json
{
  "summary": {
    "risk_score": 8.3,
    "risk_level": "high|medium|low",
    "total_articles": 450,
    "critical_alerts": 12,
    "trending_threats": 4,
    "total_cves": 89,
    "exploited_cves": 71
  },
  "attack_patterns": [...],
  "cves": [...],
  "threat_actors": [...],
  "attack_surfaces": [...],
  "insights": {...}
}
```

## Performance Considerations

### RSS Feed Fetching
- Uses parallel workers (default: 10, configurable via MAX_WORKERS)
- ThreadPoolExecutor for I/O-bound operations
- Typical run time: 20-60 seconds for 100+ feeds

### Memory Usage
- Python pipeline: 100-200MB
- Node.js dev server: 200-400MB
- Build artifacts: 50-200MB (historical data)

### Caching
- React Query caches API responses (5-minute stale time)
- Category metadata precomputed
- Incremental updates via DAYS_BACK parameter

## Deployment

### k5-security-news
- Build: `cd k5-security-news/web && npm run build`
- Output: `k5-security-news/web/dist/`
- Options: Cloudflare Pages, GitHub Pages, Docker, nginx

### 4u
- Docker: `cd 4u && docker-compose up --build`
- Manual: `python 4u.py && cd front && python -m http.server 8000`

### GitHub Actions
The k5-security-news project includes workflows:
- `update_news_json.yml` - Hourly: fetch → archive → trends → sync
- `morning_call.yml` - Daily: LLM briefing (requires OPENAI_API_KEY)

## Security Notes

### Input Validation
- HTML sanitization with `bleach` library
- Allowed tags: a, p, ul, ol, li, br, strong, em, b, i, code, pre, blockquote, span, div
- URL validation for links
- JSON schema validation

### No User Data
- Static file generation only
- No cookies (except optional theme preference)
- No user tracking or analytics
- No external API calls (except optional OpenAI for briefings)

## Troubleshooting

### No items appearing in web app
1. Check data file exists: `ls -lh k5-security-news/data/news_recent.json`
2. Verify sync ran: `./k5-security-news/scripts/sync_web_data.sh`
3. Check feed errors: `cat k5-security-news/data/archive/feed_errors_latest.json`
4. Clear browser cache and reload

### Pipeline fails
1. Check Python dependencies: `pip install -r requirements.txt`
2. Validate OPML: `xmllint --noout source/feeds.xml`
3. Check network connectivity
4. Increase timeout: `REQUEST_TIMEOUT=60 python scripts/fetch_news.py`

### Web app build fails
1. Check Node version: `node --version` (need 18+)
2. Clean install: `rm -rf node_modules package-lock.json && npm install`
3. Check for TypeScript errors: `npm run build`

## Project Navigation

- **k5-security-news/CLAUDE.md** - Complete k5 architecture documentation
- **k5-security-news/web/PAGES_DOCUMENTATION.md** - React component docs
- **tree.md** - Visual project structure
- **core/k5.md** - K5 vertical workflow
- **core/4u.md** - 4U vertical workflow
- **4u/README.md** - 4U standalone docs
- **readd/old/README.md** - GDELT implementation docs
