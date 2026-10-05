"""Backfill screenshots for already-exported Markdown job files."""

from __future__ import annotations

import re
import sqlite3
import sys
import time
from pathlib import Path

from job_scraper.core.markdown_export import (
    screenshot_relpath,
    set_screenshot_line,
    slugify,
)
from job_scraper.core.screenshots import capture_element
from job_scraper.sites.base import FetchStrategy
from job_scraper.sites.registry import SITE_REGISTRY

_SOURCE_RE = re.compile(r"^- Source:\s*(.+)$", re.MULTILINE)


def _stale_stems(site_id: str, db_path: str | None) -> set[str]:
    """Return markdown stems of jobs marked stale in the DB (read-only)."""
    if not db_path or not Path(db_path).is_file():
        return set()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT listing_id, title FROM jobs WHERE site_id = ? AND is_stale = 1",
            (site_id,),
        ).fetchall()
    finally:
        conn.close()
    return {f"{site_id}-{lid}-{slugify(title)}" for lid, title in rows}


def backfill_screenshots(
    site_id: str,
    jobs_dir: str,
    screenshots_dir: str,
    missing_only: bool = False,
    delay: float = 1.0,
    db_path: str | None = None,
    include_stale: bool = False,
) -> dict[str, int]:
    """Capture screenshots for every job file of ``site_id``.

    Captures run sequentially, sleeping ``delay`` seconds between attempts to
    be polite to the site. A failed capture never stops the run. When ``db_path``
points to an existing database and ``include_stale`` is False, postings the
scraper marked stale are skipped (``skipped_stale``).
    """
    if site_id not in SITE_REGISTRY:
        raise ValueError(f"Unknown site_id: {site_id}")
    adapter = SITE_REGISTRY[site_id]
    selector = adapter.screenshot_selector
    stealth = adapter.fetch_strategy == FetchStrategy.STEALTH

    counts = {
        "attempted": 0,
        "captured": 0,
        "failed": 0,
        "skipped_existing": 0,
        "skipped_no_selector": 0,
        "skipped_blocked": 0,
        "skipped_stale": 0,
    }
    stale_stems = (
        set() if include_stale else _stale_stems(site_id, db_path)
    )
    md_files = sorted(Path(jobs_dir).glob(f"{site_id}-*.md"))

    if selector is None:
        counts["skipped_no_selector"] = len(md_files)
        return counts

    for md in md_files:
        stem = md.stem
        if stem in stale_stems:
            counts["skipped_stale"] += 1
            continue
        png = Path(screenshots_dir) / f"{stem}.png"
        match = _SOURCE_RE.search(md.read_text())
        if not match:
            counts["failed"] += 1
            continue
        if missing_only and png.exists():
            counts["skipped_existing"] += 1
            set_screenshot_line(str(md), screenshot_relpath(stem))
            continue
        if counts["attempted"] > 0 and delay > 0:
            time.sleep(delay)
        counts["attempted"] += 1
        try:
            ok = capture_element(
                match.group(1).strip(),
                selector,
                str(png),
                stealth=stealth,
                hide_selectors=adapter.screenshot_hide_selectors,
                pre_actions=adapter.screenshot_pre_actions,
                skip_selectors=adapter.screenshot_skip_selectors,
                min_height=adapter.screenshot_min_height,
                gone_check=adapter.gone_check(),
            )
        except Exception as exc:  # noqa: BLE001 - one failure must not stop the run
            print(f"Screenshot failed for {md.name}: {exc}", file=sys.stderr)
            ok = False
        if ok is True:
            counts["captured"] += 1
            set_screenshot_line(str(md), screenshot_relpath(stem))
        elif ok is False:
            counts["failed"] += 1
        elif ok is None:
            counts["skipped_blocked"] += 1
    return counts
