# CLAUDE.md - K5 Security News Architecture Guide

This file provides comprehensive guidance to Claude Code and developers working with the K5 Security News Feed codebase.

---

## Project Overview

**K5 Security News Feed** is a fully automated, enterprise-grade cybersecurity news aggregation, normalization, archiving, and threat intelligence platform. It:

- Collects content from 100+ RSS security feeds
- Classifies articles using 23 configurable smart groups
- Performs threat intelligence analysis (risk scoring, velocity detection, attack patterns)
- Generates historical archives (monthly/yearly) with automated deduplication
- Provides optional LLM-powered SOC morning briefings
- Serves multiple front-end dashboards via a modern React SPA
- Runs entirely serverless on GitHub Pages + GitHub Actions (or Docker locally)

**Key Design Principle**: Zero hardcoding. Categories, threat actors, attack patterns, and smart groups are all externally configurable.

---

## System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ OPML Feed Definitions (source/feeds.xml)                        │
│ └─ 100+ RSS feeds organized into categories                     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Data Ingestion Pipeline (news_fetcher package)                  │
│ └─ Parallel RSS fetching (10 workers)                           │
│ └─ HTML sanitization (bleach library)                           │
│ └─ Smart group classification (23 groups, non-exclusive)        │
│ └─ Promotional content filtering                                │
│ └─ Curated item detection (high-signal items)                   │
│ Outputs: data/news_recent.json, data/archive/promo_filtered_*  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ├─────────────────────────────────┐
                        │                                 │
                        ▼                                 ▼
        ┌──────────────────────────┐      ┌──────────────────────┐
        │ Archive Processing       │      │ Threat Intelligence  │
        │ (archiver package)        │      │ (trends_analyzer)    │
        │                          │      │                      │
        │ • Monthly archives       │      │ • Risk scoring       │
        │ • Yearly archives        │      │ • Velocity analysis  │
        │ • Promo aggregation      │      │ • Attack patterns    │
        │ • Deduplication          │      │ • CVE analysis       │
        │                          │      │ • Threat actors      │
        │ Outputs:                 │      │ • Attack surfaces    │
        │ data/archive/            │      │ • Actionable insights│
        └──────────────┬───────────┘      │                      │
                       │                  │ Outputs:             │
                       │                  │ data/trends.json     │
                       │                  └──────────┬───────────┘
                       │                             │
                       └─────────────────┬───────────┘
                                         │
                                         ▼
                    ┌────────────────────────────────────┐
                    │ Web Data Sync (sync_web_data.sh)   │
                    │ rsync data/ → web/public/data/     │
                    └────────────────┬───────────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────────┐
                    │ React Web Application (web/)       │
                    │                                    │
                    │ Routes:                            │
                    │ • / (News Feed)                    │
                    │ • /archive (History Browser)       │
                    │ • /trends (Threat Intelligence)    │
                    │ • /morning-call (SOC Briefing)     │
                    │ • /threat-actors/* (Actor Timeline)│
                    └────────────────────────────────────┘
```

---

## Repository Structure

### Key Directories

```
k5-security-news/
├── source/
│   └── feeds.xml                    # OPML feed definitions (100+ feeds)
│                                    # Categories auto-discovered from this file
│
├── data/                            # Generated JSON outputs (synced to web/)
│   ├── news_recent.json             # Latest 30 days of articles
│   ├── category_metadata.json       # Category mappings (auto-generated)
│   ├── trends.json                  # Threat intelligence analytics
│   ├── archive/                     # Historical data
│   │   ├── monthly/<year>/          # Monthly archives
│   │   ├── yearly/                  # Yearly archives
│   │   ├── promo/monthly/           # Promotional items by feed
│   │   ├── feed_errors_latest.json  # Feed health/error reports
│   │   └── daily_report_latest.json # Latest LLM briefing (optional)
│   └── archive.html                 # Legacy archive page
│
├── scripts/                         # Python data pipeline
│   ├── fetch_news.py                # CLI entry point for ingestion
│   ├── build_category_metadata.py   # Generate category metadata from OPML
│   ├── archive_news.py              # CLI entry point for archiving
│   ├── create_trends.py             # CLI entry point for trends analysis
│   ├── build_daily_report.py        # Optional: LLM-powered briefings
│   ├── sync_web_data.sh             # rsync data/ to web/public/data/
│   ├── run_pipeline.sh              # Orchestrates pipeline (no briefing)
│   ├── run_full_pipeline.sh         # Orchestrates pipeline with briefing
│   │
│   ├── news_fetcher/                # Modular ingestion package (v2.0.0)
│   │   ├── __init__.py              # Exports: Config, FeedProcessor
│   │   ├── config.py                # Configuration constants
│   │   ├── processor.py             # Main feed processing engine
│   │   ├── category_loader.py       # OPML parser, category extraction
│   │   ├── smart_groups.py          # 23 configurable classification rules
│   │   ├── classifiers.py           # Classification helper functions
│   │   ├── parsers.py               # HTML sanitization, date parsing
│   │   ├── filters.py               # Promo/curated content detection
│   │   └── README.md                # Internal package docs
│   │
│   ├── archiver/                    # Modular archive package (v2.0.0)
│   │   ├── __init__.py              # Exports: Config, ArchiveProcessor
│   │   ├── config.py                # Configuration and paths
│   │   ├── processor.py             # Main orchestrator
│   │   ├── io_utils.py              # JSON I/O with error handling
│   │   ├── date_utils.py            # Date bucketing, validation
│   │   ├── merge.py                 # Item merging, deduplication
│   │   ├── promo.py                 # Promotional item aggregation
│   │   └── README.md                # Internal package docs
│   │
│   ├── trends_analyzer/             # Modern threat intelligence (v2.1.0)
│   │   ├── __init__.py              # Exports all analyzers, metrics
│   │   ├── config.py                # Attack patterns, MITRE ATT&CK, surfaces
│   │   ├── processor.py             # TrendsProcessor orchestrator
│   │   ├── metrics.py               # Risk scoring algorithms
│   │   ├── analyzers.py             # 4 specialized analyzers
│   │   ├── insights.py              # AI-driven recommendations
│   │   └── README.md                # Internal package docs
│   │
│   ├── config/
│   │   └── threat_actors.py         # 400+ threat actor names
│   │
│   └── requirements.txt             # Python dependencies
│
├── web/                             # React SPA (Vite + TypeScript)
│   ├── public/
│   │   └── data/                    # Synced from ../data/ (rsync)
│   │       ├── news_recent.json
│   │       ├── category_metadata.json
│   │       ├── trends.json
│   │       └── archive/
│   │
│   ├── src/
│   │   ├── App.tsx                  # Main app routing
│   │   ├── main.tsx                 # Vite entry point
│   │   ├── index.css                # Global styles
│   │   ├── components/              # Reusable UI components
│   │   │   └── ui/                  # shadcn-ui primitives
│   │   ├── pages/                   # Route pages
│   │   │   ├── Index.tsx            # News feed (/, /trends)
│   │   │   ├── Trends.tsx           # Threat intelligence dashboard
│   │   │   ├── Archive.tsx          # Archive browser
│   │   │   ├── MorningCall.tsx      # Briefing viewer
│   │   │   ├── ThreatActorTaxonomy.tsx  # Actor taxonomy
│   │   │   ├── ThreatActorDetail.tsx    # Actor detail page
│   │   │   └── NotFound.tsx         # 404 page
│   │   ├── data/                    # Data loading hooks
│   │   │   ├── newsData.ts          # news_recent.json loader
│   │   │   ├── trendsData.ts        # trends.json loader
│   │   │   └── categoryData.ts      # category_metadata.json loader
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── lib/                     # Utility functions
│   │   └── vite-env.d.ts            # Vite type definitions
│   │
│   ├── package.json                 # Node.js dependencies
│   ├── vite.config.ts               # Vite build configuration
│   ├── tsconfig.json                # TypeScript configuration
│   ├── tailwind.config.ts           # Tailwind CSS configuration
│   ├── dist/                        # Built output (Vite)
│   └── node_modules/                # npm packages
│
├── docker/                          # Docker support
│   ├── docker-compose.yml           # Orchestrates data + frontend services
│   ├── Dockerfile                   # Frontend (Node + Caddy)
│   ├── Dockerfile.data              # Data pipeline (Python)
│   ├── Caddyfile                    # Caddy web server config
│   └── nginx.conf                   # Legacy nginx config
│
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md              # Detailed architecture
│   ├── SETUP.md                     # Installation guide
│   ├── TRENDS.md                    # Threat intelligence guide
│   └── PIPELINE.md                  # Pipeline execution guide
│
├── .github/workflows/               # GitHub Actions automation
│   ├── update_news_json.yml         # Hourly: fetch/archive/trends
│   ├── build_news_archive.yml       # Daily: archive/trends (deprecated)
│   └── morning_call.yml             # Daily: LLM briefing (optional)
│
├── CLAUDE.md                        # This file
├── README.md                        # Project overview
├── SETUP.md                         # Setup instructions
├── ARCHITECTURE.md                  # Architecture docs
└── LICENSE                          # GNU AGPL v3.0
```

---

## Modular Python Architecture

### 1. news_fetcher Package (v2.0.0)

**Purpose**: Fetch, normalize, classify, and filter RSS feeds.

**Structure**:
- `config.py` - Configuration constants
- `processor.py` - Main orchestrator (FeedProcessor class)
- `category_loader.py` - OPML parser, dynamic category extraction
- `smart_groups.py` - 23 classification rules (externally configurable)
- `parsers.py` - HTML sanitization (bleach), date parsing
- `classifiers.py` - Classification logic
- `filters.py` - Promotional content filtering, curated item detection

**Key Classes**:
- `Config` - Configuration object with defaults
- `FeedProcessor` - Main pipeline orchestrator

**Usage**:
```python
from news_fetcher import Config, FeedProcessor

config = Config()
config.days_back = 60
config.max_workers = 20

processor = FeedProcessor(config)
results = processor.process()  # Returns: {"items": [...], "stats": {...}}
processor.save_results(results)  # Writes news_recent.json, error reports
```

**Features**:
- Parallel processing (ThreadPoolExecutor, configurable workers)
- Dynamic category loading from OPML (no hardcoding)
- 23 smart groups (non-exclusive tagging)
- Promotional content filtering
- Curated item detection
- Error categorization (parse/connection/other)
- Incremental updates (respects DAYS_BACK)
- HTML sanitization (preserves links, removes scripts)

**Output Files**:
- `data/news_recent.json` - Processed articles
- `data/archive/feed_errors_latest.json` - Feed health report
- `data/archive/promo_filtered_*.json` - Filtered promotional items

---

### 2. archiver Package (v2.0.0)

**Purpose**: Build historical archives and aggregate promotional content.

**Structure**:
- `config.py` - Configuration and paths
- `processor.py` - Main orchestrator (ArchiveProcessor class)
- `io_utils.py` - JSON reading/writing with error handling
- `date_utils.py` - Date parsing, month/year bucketing
- `merge.py` - Item merging, deduplication logic
- `promo.py` - Promotional item aggregation

**Key Classes**:
- `Config` - Configuration object with archive paths
- `ArchiveProcessor` - Main pipeline orchestrator

**Usage**:
```python
from archiver import Config, ArchiveProcessor

processor = ArchiveProcessor()
stats = processor.process()
# Returns: {
#   "monthly_archives": 12,
#   "yearly_archives": 2,
#   "promo_files": 3,
#   "items_merged": 1500,
#   "duplicates_removed": 45
# }
```

**Features**:
- Idempotent processing (safe to run multiple times)
- Deduplication by link (keeps most recent published_ts)
- Date validation (filters future dates)
- Monthly/yearly archive generation
- Promotional content aggregation by feed
- Progress tracking and error reporting

**Output Files**:
- `data/archive/monthly/<year>/<year>-<month>.json` - Monthly data
- `data/archive/yearly/<year>.json` - Yearly data
- `data/archive/promo/monthly/<year>/promo_*.json` - Promotional aggregates

---

### 3. trends_analyzer Package (v2.1.0)

**Purpose**: Enterprise-grade threat intelligence analysis.

**Structure**:
- `config.py` - Attack patterns, MITRE ATT&CK mappings, surfaces, thresholds
- `processor.py` - TrendsProcessor orchestrator
- `analyzers.py` - 4 specialized analyzer classes
- `metrics.py` - Risk scoring, velocity calculation algorithms
- `insights.py` - InsightsGenerator for AI-driven recommendations

**Key Classes**:

1. **TrendsProcessor** - Main orchestrator
   - Loads and filters news by time windows (7d, 30d, 90d)
   - Runs all analyzers in sequence
   - Aggregates results into comprehensive report
   - Generates insights

2. **AttackPatternAnalyzer** - Pattern detection
   - Detects 10 attack patterns (ransomware, supply chain, etc.)
   - Calculates velocity (surging/rising/stable/declining)
   - Maps to MITRE ATT&CK techniques
   - Assigns multi-factor risk scores

3. **CVEAnalyzer** - CVE/vulnerability tracking
   - Extracts CVEs from articles
   - Classifies severity (critical/high/medium/low)
   - Detects active exploitation
   - Identifies affected vendors

4. **ThreatActorAnalyzer** - Threat actor tracking
   - Identifies 400+ threat actors
   - Builds daily timeline
   - Calculates activity levels
   - Tracks actor correlations

5. **AttackSurfaceAnalyzer** - Attack surface assessment
   - Identifies 5 attack surfaces
   - Calculates surface-specific risk
   - Tracks incident distribution
   - Weights surfaces by severity

6. **InsightsGenerator** - Recommendation engine
   - AI-driven critical actions
   - Watch lists (monitoring items)
   - Role-based insights (CISO/SOC/Admins)
   - Context-aware messaging

**Usage**:
```python
from trends_analyzer import TrendsProcessor, TrendsConfig
from config.threat_actors import get_threat_actor_names

config = TrendsConfig()
threat_actors = get_threat_actor_names()  # Load 400+ actors

processor = TrendsProcessor(config, threat_actors)
trends_data = processor.process(items, time_range_days=30)

# Returns:
# {
#   "summary": {
#     "risk_score": 8.5,
#     "risk_level": "high",
#     "total_articles": 450,
#     "critical_alerts": 12,
#     "trending_threats": 3,
#     "total_cves": 85,
#     "exploited_cves": 42
#   },
#   "attack_patterns": [...],
#   "cves": [...],
#   "threat_actors": [...],
#   "attack_surfaces": [...],
#   "insights": {...}
# }
```

**Features**:
- Multi-factor risk scoring (0-10 scale)
- Velocity analysis (trend detection)
- 10 attack patterns with MITRE ATT&CK mapping
- 249+ CVEs analysis with exploitation tracking
- 400+ threat actors with daily timeline
- 5 attack surfaces with severity distribution
- Graceful error handling and degradation
- Structured logging with progress tracking

**Output**:
- `data/trends.json` - Comprehensive threat intelligence report

---

## Data Pipeline

### Pipeline Execution Flow

```bash
# Option 1: Core pipeline (recommended)
python scripts/fetch_news.py          # Step 1: Fetch + classify
python scripts/build_news_archive.py  # Step 2: Archive + deduplicate
python scripts/create_trends.py       # Step 3: Threat intelligence
./scripts/sync_web_data.sh            # Step 4: Sync to web app

# Option 2: All-in-one (convenience wrapper)
./scripts/run_pipeline.sh             # Runs steps 1-4

# Option 3: With optional LLM briefing
./scripts/run_full_pipeline.sh        # Runs steps 1-4 + LLM briefing
```

### Step-by-Step Breakdown

**Step 1: Fetch News** (`fetch_news.py`)
- Reads `source/feeds.xml` (OPML format)
- Fetches RSS feeds in parallel (10 concurrent workers)
- Normalizes dates, sanitizes HTML
- Extracts category from OPML group
- Classifies into smart groups (non-exclusive)
- Filters promotional content
- Detects curated items (high-signal)
- Deduplicates by link (keeps most recent)
- Outputs: `data/news_recent.json`

**Step 2: Build Archives** (`archive_news.py`)
- Reads `data/news_recent.json`
- Groups articles by month/year
- Merges with existing archives (idempotent)
- Removes duplicates by link
- Validates dates (filters future dates)
- Aggregates promotional items by feed
- Outputs: `data/archive/monthly/`, `data/archive/yearly/`, `data/archive/promo/`

**Step 3: Generate Trends** (`create_trends.py`)
- Loads `data/news_recent.json`
- Initializes TrendsProcessor
- Runs 5 analyzers (attack patterns, CVEs, threat actors, surfaces, insights)
- Calculates risk scores across time windows (7d, 30d, 90d)
- Generates actionable insights
- Outputs: `data/trends.json`

**Step 4: Sync to Web** (`sync_web_data.sh`)
- Uses rsync to copy `data/` → `web/public/data/`
- Preserves symlinks and timestamps
- Safe for multiple runs (idempotent)
- Required before building React app

**Optional Step 5: LLM Briefing** (`build_daily_report.py`)
- Reads `data/news_recent.json`
- Filters curated items from last 24 hours
- Calls OpenAI API (Responses format)
- Generates SOC-oriented markdown summary
- Outputs: `data/archive/daily_report_latest.json`, `data/archive/daily_report_YYYY-MM-DD.json`

---

## Data Schemas

### news_recent.json

```json
{
  "generated_at": "2024-12-16T14:30:00Z",
  "days_back": 30,
  "total_items": 1245,
  "items": [
    {
      "title": "Critical RCE in Exchange Server",
      "summary": "Plain text summary without HTML tags",
      "summary_html": "<p>HTML summary with <a href='...'>preserved links</a></p>",
      "link": "https://example.com/article",
      "source": "SecurityWeek",
      "type": "news",
      "type_label": "News",
      "published": "2024-12-16T10:00:00Z",
      "published_ts": 1734344400,
      "smart_groups": ["Vulnerabilities / CVEs", "Windows / Microsoft"],
      "curated": true
    }
  ]
}
```

### category_metadata.json

```json
{
  "categories": {
    "general": "General",
    "vulnerabilities": "Vulnerabilities",
    "ransomware": "Ransomware",
    ...
  },
  "generated_at": "2024-12-16T14:00:00Z"
}
```

### trends.json

```json
{
  "summary": {
    "risk_score": 8.3,
    "risk_level": "high",
    "total_articles": 450,
    "critical_alerts": 12,
    "trending_threats": 4,
    "total_cves": 89,
    "exploited_cves": 71,
    "time_range_days": 30
  },
  "attack_patterns": [
    {
      "pattern": "ransomware",
      "label": "Ransomware Activity",
      "velocity": "rising",
      "risk_score": 9.2,
      "count": 45,
      "mitre_techniques": ["T1486"]
    }
  ],
  "cves": [
    {
      "cve_id": "CVE-2024-1234",
      "severity": "critical",
      "exploited": true,
      "mentions": 12,
      "risk_score": 9.8
    }
  ],
  "threat_actors": [
    {
      "actor_name": "Lazarus",
      "mentions": 8,
      "risk_score": 8.9,
      "activity_level": "high"
    }
  ],
  "attack_surfaces": [
    {
      "surface": "endpoint",
      "risk_score": 8.5,
      "incidents": 34
    }
  ],
  "insights": {
    "critical_actions": [
      "Patch CVE-2024-1234 immediately - actively exploited in the wild"
    ],
    "watch_list": [
      "Monitor Lazarus activity - increased targeting of financial institutions"
    ]
  }
}
```

---

## Configuration & Customization

### Smart Groups (23 Categories)

Edit `scripts/news_fetcher/smart_groups.py`:

```python
SMART_GROUP_RULES = [
    ("Ransomware", ["ransomware", "lockbit", "alphv", ...]),
    ("Vulnerabilities / CVEs", ["cve-", "vulnerability", "rce", ...]),
    # Add/modify groups here - matched case-insensitively against title+summary
]
```

Categories can overlap - items can belong to multiple groups.

### Attack Patterns & MITRE Mappings

Edit `scripts/trends_analyzer/config.py`:

```python
ATTACK_PATTERNS = {
    "ransomware": {
        "label": "Ransomware Activity",
        "severity": "critical",
        "keywords": ["ransomware", "locker", ...],
        "mitre": ["T1486"],  # Impact: Encrypt data
        "description": "Ransomware attacks and gang activity"
    },
    # Add/modify patterns here
}
```

### Threat Actors

Edit `scripts/config/threat_actors.py`:

```python
# 400+ threat actors maintained here
THREAT_ACTORS = [
    ("APT28", "state_actor"),
    ("Lazarus", "state_actor"),
    # Add/modify actors here
]
```

### Attack Surfaces

Edit `scripts/trends_analyzer/config.py`:

```python
ATTACK_SURFACES = {
    "endpoint": {
        "risk_multiplier": 1.2,
        "keywords": ["workstation", "endpoint", ...],
        "description": "Endpoint security incidents"
    },
    # 5 surfaces total: endpoint, cloud, network, data, identity
}
```

### Feed Categories

Edit `source/feeds.xml` directly - categories are auto-discovered:

```xml
<outline title="Ransomware News" text="Ransomware News">
  <outline type="rss" title="Feed Title" xmlUrl="https://example.com/feed" />
</outline>
```

Then run:
```bash
python scripts/build_category_metadata.py  # Regenerates category_metadata.json
```

---

## Web Application (React SPA)

### Architecture

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Framework**: shadcn-ui + Tailwind CSS
- **Routing**: React Router v6
- **Charts**: Recharts
- **State Management**: React Query (@tanstack/react-query)
- **Form Handling**: React Hook Form
- **Validation**: Zod

### Routes

| Route | Component | Data Source | Purpose |
|-------|-----------|-------------|---------|
| `/` | Index.tsx | news_recent.json | News feed with filtering |
| `/archive` | Archive.tsx | archive/yearly/*.json | Historical archive browser |
| `/trends` | Trends.tsx | trends.json | Threat intelligence dashboard |
| `/morning-call` | MorningCall.tsx | daily_report_latest.json | SOC briefing viewer |
| `/threat-actors/:taxonomyId` | ThreatActorTaxonomy.tsx | trends.json | Actor taxonomy |
| `/threat-actor/:actorName` | ThreatActorDetail.tsx | trends.json | Individual actor details |

### Key Components

**Data Loaders** (`src/data/`):
- `newsData.ts` - Loads and filters news_recent.json
- `trendsData.ts` - Loads trends.json with caching
- `categoryData.ts` - Loads category_metadata.json

**Custom Hooks** (`src/hooks/`):
- Data fetching with React Query
- Category filtering
- Search and sort utilities

**UI Components** (`src/components/`):
- NewsCard - Individual article display
- CategoryFilter - Category selector
- TrendChart - Recharts visualizations
- DateRange - Date range picker

### Development

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm run build      # Production build to web/dist/
npm run preview    # Preview production build
npm run lint       # Run ESLint
```

### Deployment

**Build Output**: `web/dist/`

**Options**:
1. **Cloudflare Pages** - Automatic deployment, point root to `/web`
2. **GitHub Pages** - Via GitHub Actions workflow
3. **Docker** - Use `docker-compose.yml` (includes Caddy server)
4. **Self-hosted** - nginx serving static files from `web/dist/`

---

## GitHub Actions Workflows

### update_news_json.yml (Hourly)

Runs every 2 hours (can be customized):
1. Fetches news from RSS feeds
2. Builds archives
3. Generates trends analytics
4. Syncs data to web app
5. Commits and pushes changes

**Trigger**: `schedule` (cron) + `workflow_dispatch` (manual)

**Permissions**: `contents: write` (for commits)

### morning_call.yml (Daily, Optional)

Runs daily at 6:15 UTC (customizable):
1. Loads curated news items (last 24 hours)
2. Calls OpenAI Responses API
3. Generates SOC-oriented briefing
4. Saves as `daily_report_latest.json`

**Requires**: `OPENAI_API_KEY` GitHub secret

**Customizable**:
- Schedule (cron expression)
- Model (gpt-5.1, gpt-4o-mini, etc.)
- Window hours (default: 24)
- Max items (default: 100)

### build_news_archive.yml (Deprecated)

Preserved for backward compatibility, but superseded by `update_news_json.yml`.

---

## Docker Setup

### Quick Start

```bash
cd docker
docker compose up --build
# Visit http://localhost:8080
```

### Services

**data**: Python pipeline container
- Runs: fetch_news.py → archive_news.py → create_trends.py
- Mounts: `../data` (read-write), `../source` (read-only)
- Env vars: DAYS_BACK, MAX_WORKERS, REQUEST_TIMEOUT

**frontend**: nginx/Caddy serving React SPA
- Depends on: `data` service
- Serves: `web/dist/` at `/`
- Serves: `../data/` at `/data/`
- Port: 8080

### Development Workflows

```bash
# Run individual scripts
docker compose run --rm data python /app/scripts/fetch_news.py

# Access container shell
docker compose exec data /bin/sh

# View logs
docker compose logs -f data
docker compose logs -f frontend

# Rebuild and restart
docker compose down
docker compose up --build
```

### Environment Variables

Create `docker/.env`:

```
DAYS_BACK=30
MAX_WORKERS=10
REQUEST_TIMEOUT=25
```

---

## Common Development Tasks

### Update Feed List

1. Edit `source/feeds.xml` directly
2. Validate XML: `xmllint --noout source/feeds.xml`
3. Run pipeline: `python scripts/fetch_news.py`
4. Regenerate metadata: `python scripts/build_category_metadata.py`

### Add New Smart Group

1. Edit `scripts/news_fetcher/smart_groups.py`
2. Add tuple: `("Group Name", ["keyword1", "keyword2", ...])`
3. Run pipeline to test

### Add New Attack Pattern

1. Edit `scripts/trends_analyzer/config.py`
2. Add to ATTACK_PATTERNS dict with MITRE mapping
3. Run trends: `python scripts/create_trends.py`

### Test Feed Changes Locally

```bash
python scripts/fetch_news.py
python scripts/build_news_archive.py
python scripts/create_trends.py
./scripts/sync_web_data.sh

cd web
npm run dev  # http://localhost:5173
```

### Debug Feed Errors

```bash
cat data/archive/feed_errors_latest.json  # Check error details
```

Error categories:
- **parse_error** - Malformed XML/RSS
- **connection_error** - Network timeout, DNS, SSL
- **other_error** - Unexpected failures

**Important**: Feeds only flagged as "error" if they produce ZERO items. Partial failures are logged as warnings.

### Review Promotional Content

```bash
cat data/archive/promo_filtered_*.json  # Filtered items for review
```

### Customize LLM Briefing

Edit `scripts/build_daily_report.py`:
- Line 40-60: System prompt
- Line 80-110: Item formatting
- Environment variables for model selection

---

## Security Considerations

### Input Validation

- HTML sanitization with `bleach` (allowed tags: a, p, ul, ol, li, br, strong, em, b, i, code, pre, blockquote, span, div)
- URL validation for links
- OPML schema validation
- JSON schema validation

### XSS Prevention

- React's built-in escaping
- Content Security Policy headers (via Caddy/nginx)
- HTML escaping in templates
- No `dangerouslySetInnerHTML` usage

### Data Privacy

- No user tracking
- No cookies (except optional theme preference)
- No external API calls (except optional OpenAI for briefings)
- Static files only

### Secrets Management

- Never commit API keys or credentials
- Use GitHub Secrets for `OPENAI_API_KEY`
- Use environment variables in Docker
- No hardcoded credentials in code

---

## Performance & Optimization

### Parallel Processing

- RSS fetching: 10 concurrent workers (configurable via MAX_WORKERS)
- Uses ThreadPoolExecutor for I/O-bound operations
- Thread-safe data structures with locks

### Caching

- OPML parsed once per run
- Category metadata precomputed
- News data cached in React Query
- Trends data cached with 5-minute stale time

### Incremental Updates

- Fetch only last N days (DAYS_BACK)
- Archive old data separately
- Deduplication by link (efficient merge)
- Efficient JSON diff for GitHub commits

### Memory Management

- Streaming JSON processing
- Generator patterns where applicable
- Limited in-memory buffers
- No full file loading (except small configs)

---

## Error Handling & Logging

### Log Levels

- `[INFO]` - Normal operation progress
- `[WARNING]` - Non-fatal issues (partial feed failures)
- `[ERROR]` - Recoverable errors (file I/O)
- `[CRITICAL]` - Unrecoverable errors

### Error Categories

**Feed Processing**:
- Parse errors (SAXParseException, invalid XML)
- Connection errors (timeout, DNS, SSL)
- Other errors (unexpected failures)

**File Operations**:
- Missing files (FileNotFoundError)
- Permission issues (PermissionError)
- Invalid JSON (json.JSONDecodeError)

**Graceful Degradation**:
- Missing feeds don't crash pipeline
- Partial data still processed
- Error reports generated for review

### Health Checks

Check these files to monitor system health:

```bash
# Feed health
cat data/archive/feed_errors_latest.json

# Recent news count
jq '.total_items' data/news_recent.json

# Trends status
jq '.summary.risk_score' data/trends.json

# GitHub Actions status
# Check .github/workflows/ logs
```

---

## Extension Points

### Add New Analyzer

```python
# 1. Create analyzer class
from trends_analyzer.analyzers import BaseAnalyzer

class CustomAnalyzer(BaseAnalyzer):
    def analyze(self, items: List[Dict]) -> Dict[str, Any]:
        # Implementation
        return results

# 2. Add to processor
from trends_analyzer.processor import TrendsProcessor

processor = TrendsProcessor(config, threat_actors)
processor.custom_analyzer = CustomAnalyzer(config)

# 3. Call in process()
custom_data = processor.custom_analyzer.analyze(items)

# 4. Add to output
trends_data["custom_analysis"] = custom_data
```

### Add New Web Route

```typescript
// web/src/App.tsx
import MyPage from './pages/MyPage';

<Routes>
  <Route path="/my-page" element={<MyPage />} />
  {/* existing routes... */}
</Routes>
```

### Add New Data Source

```typescript
// web/src/data/myData.ts
export const useMyData = () => {
  return useQuery({
    queryKey: ['myData'],
    queryFn: async () => {
      const response = await fetch('/data/my_data.json');
      return response.json();
    },
  });
};
```

---

## Dependencies

### Python (3.11+)

- `feedparser>=6.0.0` - RSS/Atom feed parsing
- `beautifulsoup4>=4.12.0` - HTML parsing and sanitization
- `openai>=1.0.0` - LLM API client (optional, for briefings only)

### Node.js (18+)

- `react@^18` - UI framework
- `react-router-dom@^6` - Routing
- `recharts@^2` - Data visualization
- `tailwindcss@^3` - CSS framework
- `shadcn-ui` - Component library
- `zod@^3` - Schema validation
- `react-query@^5` - Data fetching

### DevDependencies

- `vite@^5` - Build tool
- `typescript@^5` - Type checking
- `eslint@^9` - Linting
- `tailwindcss@^3` - CSS compilation

---

## Deployment Checklist

Before deploying:

1. Validate OPML: `xmllint --noout source/feeds.xml`
2. Run pipeline: `./scripts/run_pipeline.sh`
3. Check data files: `ls -lh data/*.json`
4. Build web app: `cd web && npm run build`
5. Test locally: `python -m http.server 8000`
6. Review trends: `jq '.summary' data/trends.json`
7. Commit changes: `git add data/ && git commit -m "..."`
8. Push to main: `git push origin main`
9. Monitor GitHub Actions workflow status
10. Verify deployment: Check web app at deployment URL

---

## Troubleshooting

### No news items showing

1. Check feed errors: `cat data/archive/feed_errors_latest.json`
2. Verify OPML: `xmllint --noout source/feeds.xml`
3. Check network: Try manually fetching a feed
4. Increase timeout: `REQUEST_TIMEOUT=60 python scripts/fetch_news.py`

### Web app not loading

1. Check data files: `ls -lh web/public/data/`
2. Verify sync: `./scripts/sync_web_data.sh`
3. Check build: `npm run build` in web/
4. Clear browser cache
5. Check console errors: F12 Developer Tools

### Trends not updating

1. Check news data: `jq '.total_items' data/news_recent.json`
2. Run trends manually: `python scripts/create_trends.py`
3. Check errors: `python scripts/create_trends.py 2>&1 | head -20`
4. Verify threat_actors loaded: Check log output

### Morning briefing not generating

1. Verify OpenAI key: `echo $OPENAI_API_KEY`
2. Check curated items: `jq '[.items[] | select(.curated)] | length' data/news_recent.json`
3. Run manually: `python scripts/build_daily_report.py`
4. Check API status: OpenAI status page

---

## Performance Metrics

### Typical Run Times

- Fetch news: 20-60 seconds (depends on feed count)
- Build archives: 5-10 seconds
- Generate trends: 10-20 seconds
- Sync to web: 2-5 seconds
- **Total pipeline**: 40-100 seconds

### Resource Usage

- Memory: 100-200MB (Python)
- CPU: Moderate (I/O-bound)
- Disk: 50-200MB (data files)
- Bandwidth: 5-20MB per run

### Data Scale

- Feeds: 100+
- Articles/month: 1,500-3,000
- Archive size: 50-100MB (full history)
- Threat actors: 400+
- Smart groups: 23

---

## References

- **README.md** - Project overview and quick start
- **docs/ARCHITECTURE.md** - Detailed system architecture
- **docs/SETUP.md** - Installation and configuration
- **docs/TRENDS.md** - Threat intelligence guide
- **docs/PIPELINE.md** - Pipeline execution guide
- **web/PAGES_DOCUMENTATION.md** - React component documentation

---

## License

GNU Affero General Public License v3.0 (AGPL-3.0)

All code is open-source and can be used, modified, and distributed under AGPL-3.0 terms.

---

## Contributing

When contributing to this project:

1. Maintain modular architecture (don't merge packages)
2. Keep configuration externalized (no hardcoding)
3. Write type hints for all Python functions
4. Use TypeScript for web code
5. Document new features in this file
6. Test changes locally before pushing
7. Follow existing code style and patterns

---
