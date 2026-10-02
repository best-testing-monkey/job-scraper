import sys
from pathlib import Path
from job_scraper.core.db import JobRepository
from job_scraper.core.filters import is_excluded
from job_scraper.core.markdown_export import slugify
from job_scraper.core.models import ListingStub
import job_scraper.core.markdown_export as markdown_export
from job_scraper.sites.registry import SITE_REGISTRY


NOT_REBUILDABLE: dict[str, str] = {
    "working_nomads": "Parse detail reads cache from list_postings (not saved)",
    "tender_link": "Parse detail reads cache from list_postings (not saved)",
    "stone_interim": "parse_detail needs the human LinkUrl from the listing API response, which is not saved in raw/ — re-scrape instead",
}


def rebuild_site(site_id: str, repo: JobRepository, jobs_dir: str, raw_dir: str) -> dict[str, int]:
    """Re-run each adapter's parse_detail over raw pages saved in raw_dir/site_id/
    and rewrite matching markdown files and DB rows.

    Returns dict with keys: rebuilt, skipped_no_db, skipped_duplicate, excluded, errors
    (all ints).
    """
    if site_id in NOT_REBUILDABLE:
        raise ValueError(f"Site {site_id} cannot be rebuilt from raw: {NOT_REBUILDABLE[site_id]}")

    if site_id not in SITE_REGISTRY:
        raise ValueError(f"Site {site_id} not in SITE_REGISTRY")

    counters = {
        "rebuilt": 0,
        "skipped_no_db": 0,
        "skipped_duplicate": 0,
        "excluded": 0,
        "errors": 0,
    }

    adapter_class = SITE_REGISTRY[site_id]
    adapter = adapter_class()

    raw_site_dir = Path(raw_dir) / site_id
    if not raw_site_dir.exists():
        return counters

    cursor = repo.conn.cursor()
    db_rows = cursor.execute(
        "SELECT listing_id, title, source_url, last_seen_at, duplicate_of FROM jobs WHERE site_id = ?",
        (site_id,)
    ).fetchall()

    for raw_file in raw_site_dir.iterdir():
        if not raw_file.is_file():
            continue

        ext = raw_file.suffix.lstrip('.')
        if ext not in ('html', 'json'):
            continue

        stem = raw_file.stem

        matching_row = None
        for row in db_rows:
            listing_id, title, source_url, last_seen_at, duplicate_of = row
            expected_stem = f"{site_id}-{listing_id}-{slugify(title)}"
            if expected_stem == stem:
                matching_row = (listing_id, title, source_url, last_seen_at, duplicate_of)
                break

        if matching_row is None:
            counters["skipped_no_db"] += 1
            continue

        listing_id, title, source_url, last_seen_at, duplicate_of = matching_row

        try:
            page_bytes = raw_file.read_bytes()
            stub = ListingStub(
                listing_id=listing_id,
                detail_url=source_url,
                title=title,
            )
            posting = adapter.parse_detail(stub, page_bytes)
        except Exception as e:
            print(f"Error parsing {raw_file.name}: {e}", file=sys.stderr)
            counters["errors"] += 1
            continue

        if is_excluded(posting):
            counters["excluded"] += 1
            continue

        if duplicate_of is not None:
            counters["skipped_duplicate"] += 1
            continue

        repo.upsert(posting, seen_at=last_seen_at)
        markdown_export.write(posting, jobs_dir)
        counters["rebuilt"] += 1

    return counters
