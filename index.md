# News Projects Overview

This directory contains multiple instances of a news aggregation and threat/trend intelligence platform. The platform ingest RSS feeds, normalizes them, analyzes trends, and provides a React dashboard to view the data.

## Project Verticals

The workspace contains several separated "verticals" (by topic or domain), each maintaining its own full or partial copy of the pipeline and UI setup:

- **`4u/`** - The original/main reference platform, containing shared Python ingestion pipeline code under `code/base/` and a React demo SPA in `web/`.
- **`k5-security-news/`** - A mature instantiation of the platform configured specifically for security and threat intelligence, complete with trend analyses and SOC daily reporting.
- **`core/`** - Appears to be an attempt at a consolidated base or structural template, containing similar `scripts/`, `code/`, `data/`, and `web/` directories.
- **`economic-4u/`** & **`economic/`** - The economy news vertical. `economic-4u/` contains a cloned full-stack pipeline, while `economic/` contains a Lovable-generated standalone frontend.
- **`storage-4u/`** & **`storage/`** - The storage news vertical. Similar to economic, there are duplicated pipeline instances and disconnected Lovable frontend clones.
- **`finnish/`** - The Finnish region news vertical, containing its own copy of the pipeline and web code.

## Current Architecture & Reusability Pain Points

All these directories effectively operate on the **same base template**, which handles:
1. Fetching RSS feeds defined via OPML files (`source/<vertical>/feeds.xml`).
2. Data normalization to output raw data (e.g., `news_recent.json`).
3. Running data and trend archiving scripts (`scripts/fetch_news.py`, `scripts/build_news_archive.py`).
4. Supplying data to a statically built front-end in `web/`.

**The Core Issue:** 
The base was not designed to be easily extensible without code duplication. The tight coupling of scripts, CI/CD tools, UI templates, and hardcoded config has led to the current situation where **deploying a new vertical requires copying the entire software stack.**

Because each vertical lives in its own standalone directory with its own `.github/workflows/`, backend scripts, and React source code:
- **Hard to configure:** Bootstrapping a new site requires heavy manual file replacing, rather than just changing a single `config.json` or setting an environment variable.
- **Drift:** Bug fixes and new UI features developed in one vertical (like `k5-security-news`) do not automatically propagate to `finnish` or `economic-4u`.
- **Maintenance Overhead:** The pipeline consumes significant duplicate resources, making Docker and server ops tedious to maintain for multiple separate repos.
- **Integration Friction:** When frontend code was handed off or updated externally (via Lovable outputs like `economic/` and `storage/`), they became disconnected from the backend directories they are supposed to serve.

## A Path Forward: Architectural Consolidation

To solve this, the projects should be refactored into a scalable architecture such as a **Monorepo Strategy (Nx or Turborepo)** or a **Single Core Engine**:

1. **Shared Python Pipeline (Core Engine)**
   Extract the `fetch_news`, `archive`, and `trends` intelligence logic into a single dedicated Python package or backend service. Instead of having multiple instances of the code, a single service could process data across all verticals by looping through a list of configurations:
   ```bash
   python scripts/fetch_news.py --vertical finnish
   python scripts/fetch_news.py --vertical economic
   ```

2. **Common React Web Template**
   Instead of duplicating the `web/` directory for every topic, maintain exactly one React codebase. The web app should dynamically adjust its branding, API data paths (e.g., `/data/{vertical}/`), and components based on the environment `VITE_VERTICAL_THEME`.

3. **Data/Config Segregation**
   Separate the code from the configuration. Directories should just hold feeds, not code:
   ```
   data-sources/
     ├── finnish/
     │   └── feeds.xml
     ├── k5/
     │   └── feeds.xml
     └── economic/
         └── feeds.xml
   ```

Adopting these patterns will drastically minimize friction when spinning up new sites, as it shifts the effort from "copying and modifying code" to simply "adding a new data config file."
