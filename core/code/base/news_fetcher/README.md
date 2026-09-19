# news_fetcher

Modern, modular RSS feed aggregation and classification system for cybersecurity news.

## Architecture

This package provides a clean separation of concerns:

- **config.py** - All configuration constants (paths, keywords, timeouts)
- **filters.py** - Content filtering (promotional, curated detection)
- **classifiers.py** - Smart group classification rules
- **parsers.py** - HTML sanitization, date parsing, OPML processing
- **processor.py** - Main feed processing engine with parallel execution

## Usage

### As a Script

```bash
python scripts/fetch_news.py

# With custom configuration
DAYS_BACK=60 MAX_WORKERS=20 python scripts/fetch_news.py
```

### As a Library

```python
from news_fetcher import Config, FeedProcessor

# Use default configuration
processor = FeedProcessor()
results = processor.process()
processor.save_results(results)

# Or customize configuration
config = Config()
config.days_back = 60
config.max_workers = 20

processor = FeedProcessor(config)
results = processor.process()
# results is a dict with: generated_at, days_back, total_items, items
```

## Design Principles

1. **Separation of Concerns** - Each module has a single, well-defined responsibility
2. **DRY** - No code duplication, reusable functions
3. **Configurability** - All constants in config.py, environment variable support
4. **Testability** - Pure functions, dependency injection, clear interfaces
5. **Maintainability** - Clean code, type hints, docstrings

## Configuration

### Categories (Dynamic from OPML)

Categories are **automatically loaded** from `source/<vertical>/feeds.xml` (for example `source/k5/feeds.xml`). No Python code changes needed!
Feeds are curated in `news.xml`, `blog.xml`, and `podcasts.xml`; run `merge_feeds.py` (or `run_pipeline.sh`) after editing them to regenerate the master OPML file.

When you add/modify feed categories in the OPML file, the system automatically:
1. Extracts all group titles
2. Generates slug mappings (e.g., "Crypto & Blockchain Security" → "crypto-blockchain-security")
3. Uses them during classification

**To change categories:**
1. Edit `source/<vertical>/{news,blog,podcasts}.xml` - add/rename `<outline>` groups
2. Run `merge_feeds.py` (or `run_pipeline.sh`) to rebuild `feeds.xml`
2. Run the script - categories are loaded dynamically
3. No Python code changes required!

### Smart Groups (Configurable)

Smart groups are defined in `smart_groups.py` for easy customization.

**To add a new smart group:**

Edit `scripts/news_fetcher/smart_groups.py`:

```python
SMART_GROUP_RULES = [
    # ...existing rules...
    ("Your New Group", [
        "keyword1",
        "keyword2",
        "keyword3",
    ]),
]
```

**To modify existing smart groups:**

Just edit the keyword lists in `smart_groups.py`. Changes take effect immediately —
including for items already in `news_recent.json`, which are re-classified on load.

**Matching rules** (`classifiers.py`):

- Keywords match on **word boundaries** (`rce` no longer matches *source*);
  a trailing `*` makes a stem (`exploit*` → exploited, exploitation).
- A rule may be `(name, {"any": [...], "require": [...], "title": True})`:
  one term from each list must match; `"title": True` looks at the title only.
- Tags are capped (`Policy.max_smart_groups`, default 3). With
  `Policy.summary_mode = "fallback"` the title decides and the summary is only
  consulted when the title matched nothing (4u uses this; it is far more precise).

### Per-vertical policy (`code/<vertical>/policy.py`)

`quality.py` loads an optional `POLICY = Policy(...)` per vertical:

| Field | Purpose |
|---|---|
| `gated_source_types`, `topic_terms`, `exempt_source_pattern` | Relevance gate: items from general feeds (by OPML category slug) must mention a topic term unless the feed title itself does. |
| `drop_arxiv_announce_types` | Drop arXiv `replace`/`cross` re-announcements (default on). |
| `curated_keywords` | Per-vertical curated list (`[]` disables the flag). |
| `aggregator_pattern` | Feeds that are never a story's primary telling (Techmeme, HN…). |
| `summary_mode`, `max_smart_groups` | Classification behaviour, see above. |
| `story_window_hours` | Window for linking tellings of one story. |

Every item also gets summary boilerplate stripped (`The post … appeared first
on`, `Read more`, arXiv `Announce Type:` prefix, title-only summaries) and
future-dated items (> 36 h ahead) are dropped.

### Stories (`stories.py`)

Different outlets' tellings of one story are linked by title-token overlap
within `story_window_hours`. Members get `story_id` / `story_size`; the primary
(earliest non-aggregator telling) gets `story_primary: true` and
`story_others: [{source, title, link, published_ts}]`. The web feed shows one
card per story with "Also reported by …".

### Add New Filters

Edit `filters.py`:

```python
def is_your_filter(text: str, patterns: List[str]) -> bool:
    # Your logic here
    pass
```

### Change HTML Sanitization

Edit `config.py`:

```python
SUMMARY_ALLOWED_TAGS.add("your_tag")
SUMMARY_ALLOWED_ATTRS["your_tag"] = {"your_attr"}
```

## Dependencies

- `feedparser>=6.0.0` - RSS/Atom feed parsing
- `beautifulsoup4>=4.12.0` - HTML sanitization (optional but recommended)

## Error Handling

The processor tracks three error types:

1. **Parse Errors** - Malformed XML, SAXParseException
2. **Connection Errors** - Timeouts, DNS failures, SSL issues
3. **Other Errors** - Unexpected failures

Feeds are only marked as errored if they produce zero items. Minor XML issues that still allow parsing are logged as warnings.

## Output

The processor generates:

- `data/news_recent.json` - Main output with classified items
- `data/archive/feed_errors_latest.json` - Error report
- `data/archive/promo_filtered_latest.json` - Promotional content report

## Thread Safety

The processor uses ThreadPoolExecutor for parallel feed fetching with thread-safe locks protecting shared data structures.
