# archiver

Modern, modular news archive management system for aggregating and deduplicating cybersecurity news items.

## Architecture

This package provides clean separation of concerns:

- **config.py** - All configuration paths
- **io_utils.py** - JSON loading and saving with error handling
- **date_utils.py** - Date parsing, validation, and bucketing
- **merge.py** - Merge and deduplication logic
- **promo.py** - Promotional content aggregation
- **processor.py** - Main archive processing engine

## Usage

### As a Script

```bash
python scripts/archive_news.py
```

### As a Library

```python
from archiver import Config, ArchiveProcessor

# Use default configuration
processor = ArchiveProcessor()
stats = processor.process()

print(f"Updated {stats['monthly_archives']} monthly archives")
print(f"Updated {stats['yearly_archives']} yearly archives")
print(f"Processed {stats['promo_files']} promo files")

# Or customize configuration
config = Config()
config.monthly_dir = Path("/custom/path/monthly")

processor = ArchiveProcessor(config)
stats = processor.process()
```

## Features

### Monthly Archives

Items are aggregated by (year, month) into:
```
data/archive/monthly/<year>/<year>-<month>.json
```

Each file contains a list of news items sorted by published_ts (descending).

### Yearly Archives

Items are aggregated by year into:
```
data/archive/yearly/<year>.json
```

### Promotional Content Aggregation

Processes `promo_filtered_*.json` debug files into monthly aggregates:
```
data/archive/promo/monthly/<year>/promo_<year>-<month>.json
```

After processing, the `promo_filtered_*.json` files are deleted.

### Deduplication

Items are deduplicated by `link` field. When duplicates exist, the item with the most recent `published_ts` is kept.

### Date Validation

Items with dates beyond current year + 1 are filtered out as invalid.

## Design Principles

1. **Separation of Concerns** - Each module has a single responsibility
2. **DRY** - No code duplication, reusable functions
3. **Idempotent** - Can be run multiple times safely
4. **Error Handling** - Graceful handling of empty/corrupted files
5. **Maintainability** - Clean code, type hints, docstrings

## Output Structure

Archive files are plain JSON arrays:

```json
[
  {
    "title": "...",
    "link": "...",
    "published": "2024-12-15T10:00:00Z",
    "published_ts": 1702638000,
    "source": "...",
    "type": "...",
    "smart_groups": [...],
    "curated": true
  },
  ...
]
```

Promo files aggregate by feed:

```json
[
  {
    "feed_title": "...",
    "xml_url": "...",
    "type_label": "...",
    "first_seen": "2024-12-01T00:00:00Z",
    "last_seen": "2024-12-15T00:00:00Z",
    "total_hits": 42,
    "examples": ["deal title 1", "deal title 2", ...]
  },
  ...
]
```

## Error Handling

- Empty files are treated as empty lists
- Corrupted JSON files are logged as warnings
- Invalid future dates are filtered out with warnings
- File deletion errors are logged but don't stop processing

## Dependencies

No external dependencies beyond Python standard library.
