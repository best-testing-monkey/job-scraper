"""Move thin PNGs aside and drop their markdown screenshot lines."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from job_scraper.core.markdown_export import remove_screenshot_line
from job_scraper.core.screenshots import _png_height


def prune_small_screenshots(
    screenshots_dir: str,
    jobs_dir: str,
    *,
    min_height: int = 100,
    sites: Sequence[str] | None = None,
    move_to: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Move PNGs shorter than min_height to move_to, drop their markdown lines.

    Scans sorted(Path(screenshots_dir).glob("*.png")), restricted to files
    starting with f"{site}-" for any site in sites (None or empty = all).

    Returns dict with keys: scanned, small, moved, markdown_updated, unreadable,
    skipped_exists. dry_run=True counts small but moves/edits nothing (moved=0,
    markdown_updated=0). dry_run=False with move_to=None raises ValueError
    before touching anything. For each PNG with height < min_height: creates
    move_to (mkdir parents), moves the file there (if a file of that name
    already exists, leaves PNG in place and counts skipped_exists), then calls
    remove_screenshot_line and counts markdown_updated when it returns True.
    Unreadable PNG files (height cannot be read) are left in place and counted
    as unreadable. Idempotent.
    """
    if not dry_run and move_to is None:
        raise ValueError("move_to is required unless dry_run")

    counters = {
        "scanned": 0,
        "small": 0,
        "moved": 0,
        "markdown_updated": 0,
        "unreadable": 0,
        "skipped_exists": 0,
    }

    # Determine site prefixes to match
    site_set = set(sites) if sites else None

    # Scan PNGs in sorted order
    screenshots_path = Path(screenshots_dir)
    pngs = sorted(screenshots_path.glob("*.png"))

    for png_path in pngs:
        stem = png_path.stem
        counters["scanned"] += 1

        # Filter by site if sites specified
        if site_set is not None:
            png_name = png_path.name
            matches_site = any(png_name.startswith(f"{site}-") for site in site_set)
            if not matches_site:
                continue

        # Read PNG height
        height = _png_height(str(png_path))
        if height is None:
            counters["unreadable"] += 1
            continue

        if height >= min_height:
            continue

        counters["small"] += 1

        if dry_run:
            continue

        # Move the file
        move_to_path = Path(move_to)
        move_to_path.mkdir(parents=True, exist_ok=True)
        target_png = move_to_path / png_path.name

        if target_png.exists():
            counters["skipped_exists"] += 1
            continue

        # Move the PNG
        shutil.move(str(png_path), str(target_png))
        counters["moved"] += 1

        # Update markdown file
        md_path = Path(jobs_dir) / f"{stem}.md"
        if remove_screenshot_line(str(md_path)):
            counters["markdown_updated"] += 1

    return counters
