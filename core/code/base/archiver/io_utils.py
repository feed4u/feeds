"""I/O utilities for loading and saving JSON files."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Cloudflare Pages refuses to deploy any asset over 25 MiB and GitHub rejects
# pushes with blobs over 100 MB, so archive files must stay under both limits.
MAX_JSON_BYTES = int(os.environ.get("ARCHIVE_MAX_JSON_BYTES", 22 * 1024 * 1024))


def cap_items_to_bytes(
    items: List[Dict[str, Any]], max_bytes: int = MAX_JSON_BYTES
) -> List[Dict[str, Any]]:
    """
    Trim a newest-first item list so its JSON serialization fits max_bytes.

    Items are expected sorted newest-first (merge_and_dedup guarantees this),
    so the oldest items are the ones dropped.
    """
    total = 2  # surrounding brackets
    kept: List[Dict[str, Any]] = []
    for item in items:
        piece = json.dumps(item, ensure_ascii=False, indent=2)
        # nesting inside the array adds 2 spaces of indentation per line
        total += len(piece.encode("utf-8")) + 2 * (piece.count("\n") + 1) + 4
        if total > max_bytes:
            break
        kept.append(item)
    return kept


def load_json_any(path: Path) -> Any:
    """
    Load JSON from file with error handling for empty/corrupted files.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON data or empty list on error
    """
    if not path.exists():
        return None

    # Check if file is empty
    if path.stat().st_size == 0:
        print(f"[WARN] Empty file found: {path}, treating as empty list")
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[WARN] Corrupted JSON file {path}: {e}, treating as empty list")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to read {path}: {e}")
        return None


def load_json_list(
    path: Path, root_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load a JSON file and return a list of items.

    Handles both:
    - List at root: [item1, item2, ...]
    - Dict with key: {"items": [item1, item2, ...]}

    Args:
        path: Path to JSON file
        root_key: Key to extract from dict (defaults to "items")

    Returns:
        List of items (empty list if file not found or invalid)
    """
    if not path.exists():
        return []

    data = load_json_any(path)

    if data is None:
        return []

    # List at root
    if isinstance(data, list):
        return data

    # Dict case
    if isinstance(data, dict):
        # Try specified root_key first
        if root_key and isinstance(data.get(root_key), list):
            return data[root_key]

        # Default to "items"
        if isinstance(data.get("items"), list):
            return data["items"]

        raise ValueError(
            f"Expected list or dict with 'items' key in {path}, "
            f"but found dict with keys: {list(data.keys())}"
        )

    raise ValueError(f"Expected list or dict in {path}, but found {type(data)}")


def save_json_list(path: Path, items: List[Dict[str, Any]]) -> None:
    """
    Save list of items to JSON file.

    Creates parent directories if needed.

    Args:
        path: Path to output JSON file
        items: List of items to save
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    capped = cap_items_to_bytes(items)
    if len(capped) < len(items):
        print(
            f"[WARN] {path}: size cap {MAX_JSON_BYTES} bytes reached, "
            f"kept {len(capped)}/{len(items)} newest items"
        )
        items = capped
    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
