#!/usr/bin/env python3
"""
Remove errored feeds from source/<vertical>/feeds.xml and create REMOVED_FEEDS.md documentation.

This script:
1. Reads feed errors from data/archive/feed_errors_latest.json
2. Creates REMOVED_FEEDS.md with all removed feeds organized by category and error type
3. Removes errored feeds from source/<vertical>/feeds.xml
4. Creates backup of the original OPML file
"""

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from path_utils import add_path_cli_arguments, load_path_config


def _resolve_paths(args):
    path_config = load_path_config(
        start=__file__,
        base_dir=args.base_dir,
        data_dir=args.data_dir,
        vertical=args.vertical,
        opml_path=args.opml_path,
        archive_dir=args.archive_dir,
    )
    error_file = path_config.archive_dir / "feed_errors_latest.json"
    feeds_xml = path_config.opml_path
    removed_doc = path_config.base_dir / "REMOVED_FEEDS.md"
    backup_xml = feeds_xml.parent / f"{feeds_xml.name}.backup"
    return path_config, error_file, feeds_xml, removed_doc, backup_xml


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove feeds that consistently fail and document removals."
    )
    add_path_cli_arguments(parser)
    return parser.parse_args()


def load_error_report(error_file: Path):
    """Load feed error report."""
    with open(error_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def organize_errors_by_category(error_data):
    """Organize errors by category and error type."""
    organized = defaultdict(lambda: defaultdict(list))

    # Process all error types
    for error_type in ['parse_errors', 'connection_errors', 'other_errors']:
        for error in error_data.get(error_type, []):
            category = error.get('type_label', 'Unknown')
            organized[category][error_type].append(error)

    return organized


def create_removed_feeds_doc(error_data, organized_errors, error_file: Path, feeds_xml: Path, base_dir: Path):
    """Create REMOVED_FEEDS.md documentation."""
    content = ["# Removed RSS Feeds", ""]
    content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        relative_source = error_file.relative_to(base_dir)
    except ValueError:
        relative_source = error_file
    content.append(f"**Source:** `{relative_source}`")
    content.append("")

    summary = error_data['summary']
    content.append("## Summary")
    content.append("")
    content.append(f"- **Total feeds with errors:** {summary['total_feeds_with_errors']}")
    content.append(f"- **Parse errors:** {summary['parse_errors_count']} (malformed XML, encoding issues)")
    content.append(f"- **Connection errors:** {summary['connection_errors_count']} (timeouts, DNS failures)")
    content.append(f"- **Other errors:** {summary['other_errors_count']} (non-XML content type, etc.)")
    content.append("")

    content.append("## Removed Feeds by Category")
    content.append("")
    try:
        feeds_relative = feeds_xml.relative_to(base_dir)
    except ValueError:
        feeds_relative = feeds_xml
    content.append(f"These feeds have been removed from `{feeds_relative}`. "
                   "You can research alternative RSS feeds for these sources.")
    content.append("")

    # Sort categories alphabetically
    for category in sorted(organized_errors.keys()):
        errors_by_type = organized_errors[category]
        total_in_category = sum(len(errors) for errors in errors_by_type.values())

        content.append(f"### {category}")
        content.append("")
        content.append(f"**{total_in_category} feeds removed**")
        content.append("")

        # Parse errors
        if 'parse_errors' in errors_by_type:
            content.append("#### Parse Errors (Malformed XML)")
            content.append("")
            for error in errors_by_type['parse_errors']:
                content.append(f"- **{error['feed_title']}**")
                content.append(f"  - URL: `{error['xml_url']}`")
                content.append(f"  - Error: {error['error_message']}")
                content.append("")

        # Connection errors
        if 'connection_errors' in errors_by_type:
            content.append("#### Connection Errors")
            content.append("")
            for error in errors_by_type['connection_errors']:
                content.append(f"- **{error['feed_title']}**")
                content.append(f"  - URL: `{error['xml_url']}`")
                content.append(f"  - Error: {error['error_message']}")
                content.append("")

        # Other errors
        if 'other_errors' in errors_by_type:
            content.append("#### Other Errors")
            content.append("")
            for error in errors_by_type['other_errors']:
                content.append(f"- **{error['feed_title']}**")
                content.append(f"  - URL: `{error['xml_url']}`")
                content.append(f"  - Error: {error['error_message']}")
                content.append("")

    # Common error patterns section
    content.append("## Common Error Patterns")
    content.append("")
    content.append("### Parse Errors")
    content.append("")
    content.append("Most common causes:")
    content.append("- Invalid XML syntax (unclosed tags, malformed entities)")
    content.append("- Encoding issues (UTF-8 vs declared encoding)")
    content.append("- HTML returned instead of XML/RSS")
    content.append("")

    content.append("### Medium.com Feeds")
    content.append("")
    content.append("Many Medium feeds failed with identical error: `<unknown>:2:751: not well-formed (invalid token)`")
    content.append("")
    content.append("Alternative approaches:")
    content.append("- Check if the author has a personal blog with RSS")
    content.append("- Use Medium's main feed and filter by author")
    content.append("- Consider using Medium's API if available")
    content.append("")

    content.append("### Non-XML Content Type")
    content.append("")
    content.append("Some URLs return HTML instead of RSS/XML. Possible fixes:")
    content.append("- Look for `/feed/`, `/rss`, or `/atom` endpoints")
    content.append("- Check website footer or header for RSS icon/link")
    content.append("- Try common RSS URL patterns (e.g., `/feed`, `/rss.xml`, `/atom.xml`)")
    content.append("")

    content.append("## Finding Replacement Feeds")
    content.append("")
    content.append("### For Vendor Blogs")
    content.append("")
    content.append("1. Visit the vendor's main website")
    content.append("2. Look for blog section")
    content.append("3. Check page source for `<link rel=\"alternate\" type=\"application/rss+xml\">`")
    content.append("4. Try common patterns:")
    content.append("   - `https://example.com/blog/feed/`")
    content.append("   - `https://example.com/feed/`")
    content.append("   - `https://example.com/rss.xml`")
    content.append("")

    content.append("### For Researcher Blogs")
    content.append("")
    content.append("1. Check if they have migrated platforms")
    content.append("2. Look for Twitter/LinkedIn for updated blog links")
    content.append("3. Try Wayback Machine to see if feed URL changed")
    content.append("")

    content.append("## Validation Tools")
    content.append("")
    content.append("Before adding replacement feeds, validate them:")
    content.append("")
    content.append("- **W3C Feed Validator:** https://validator.w3.org/feed/")
    content.append("- **feedparser (Python):** Test parsing locally")
    content.append("- **curl:** Check HTTP status and content type")
    content.append("")
    content.append("```bash")
    content.append("# Check if URL returns XML")
    content.append("curl -I https://example.com/feed/")
    content.append("")
    content.append("# Test with feedparser")
    content.append("python -c \"import feedparser; print(feedparser.parse('URL'))\"")
    content.append("```")
    content.append("")

    content.append("## Notes")
    content.append("")
    backup_path = feeds_xml.parent / f"{feeds_xml.name}.backup"
    try:
        backup_display = backup_path.relative_to(base_dir)
    except ValueError:
        backup_display = backup_path
    content.append(f"- Backup of original feeds.xml saved to: `{backup_display}`")
    content.append(f"- Run `./scripts/run_pipeline.sh` after updating `{feeds_relative}` to test new feeds")
    content.append("- Check `data/archive/feed_errors_latest.json` after pipeline runs to verify fixes")
    content.append("")

    return "\n".join(content)


def remove_feeds_from_xml(error_data, feeds_xml: Path, backup_xml: Path, base_dir: Path):
    """Remove errored feeds from feeds.xml."""
    # Create backup
    import shutil
    shutil.copy2(feeds_xml, backup_xml)
    try:
        backup_display = backup_xml.relative_to(base_dir)
    except ValueError:
        backup_display = backup_xml
    print(f"[INFO] Created backup: {backup_display}")

    # Collect all errored URLs
    errored_urls = set()
    for error_type in ['parse_errors', 'connection_errors', 'other_errors']:
        for error in error_data.get(error_type, []):
            errored_urls.add(error['xml_url'])

    print(f"[INFO] Removing {len(errored_urls)} errored feeds from feeds.xml...")

    # Parse XML
    tree = ET.parse(feeds_xml)
    root = tree.getroot()

    # Track statistics
    removed_count = 0
    categories_affected = set()

    # Find and remove errored feeds
    for category in root.findall('.//outline[@title]'):
        if category.get('type') == 'rss':
            continue  # Skip feed-level outlines

        category_title = category.get('title')
        feeds_to_remove = []

        for feed in category.findall('outline[@type="rss"]'):
            xml_url = feed.get('xmlUrl')
            if xml_url in errored_urls:
                feeds_to_remove.append(feed)
                removed_count += 1
                categories_affected.add(category_title)

        # Remove feeds from category
        for feed in feeds_to_remove:
            category.remove(feed)

    # Save cleaned XML
    tree.write(feeds_xml, encoding='utf-8', xml_declaration=True)

    print(f"[INFO] Removed {removed_count} feeds from {len(categories_affected)} categories")
    print(f"[INFO] Cleaned feeds.xml saved")

    return removed_count, categories_affected


def main():
    """Main execution."""
    args = _parse_args()
    path_config, error_file, feeds_xml, removed_doc, backup_xml = _resolve_paths(args)
    print("=" * 60)
    print("Remove Errored Feeds from feeds.xml")
    print("=" * 60)
    print("")

    # Load error report
    try:
        error_display = error_file.relative_to(path_config.base_dir)
    except ValueError:
        error_display = error_file
    print(f"[1/3] Loading error report from {error_display}...")
    error_data = load_error_report(error_file)
    print(f"      Found {error_data['summary']['total_feeds_with_errors']} feeds with errors")
    print("")

    # Create documentation
    try:
        doc_display = removed_doc.relative_to(path_config.base_dir)
    except ValueError:
        doc_display = removed_doc
    print(f"[2/3] Creating documentation: {doc_display}...")
    organized_errors = organize_errors_by_category(error_data)
    doc_content = create_removed_feeds_doc(error_data, organized_errors, error_file, feeds_xml, path_config.base_dir)

    with open(removed_doc, 'w', encoding='utf-8') as f:
        f.write(doc_content)

    print(f"      Documentation created ({len(organized_errors)} categories)")
    print("")

    # Remove feeds from XML
    try:
        feeds_display = feeds_xml.relative_to(path_config.base_dir)
    except ValueError:
        feeds_display = feeds_xml
    print(f"[3/3] Removing errored feeds from {feeds_display}...")
    removed_count, categories = remove_feeds_from_xml(error_data, feeds_xml, backup_xml, path_config.base_dir)
    print("")

    # Summary
    print("=" * 60)
    print("Cleanup Complete!")
    print("=" * 60)
    print("")
    print(f"✓ Removed {removed_count} errored feeds")
    print(f"✓ Affected categories: {len(categories)}")
    print(f"✓ Documentation: {doc_display}")
    try:
        backup_display = backup_xml.relative_to(path_config.base_dir)
    except ValueError:
        backup_display = backup_xml
    print(f"✓ Backup saved: {backup_display}")
    print("")
    print("Next steps:")
    print("  1. Review REMOVED_FEEDS.md")
    print("  2. Research replacement RSS feeds")
    print(f"  3. Add new feeds to {feeds_display}")
    print("  4. Run ./scripts/run_pipeline.sh to test")
    print("")


if __name__ == '__main__':
    main()
