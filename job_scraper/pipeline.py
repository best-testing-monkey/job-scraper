import sys
from datetime import datetime
from pathlib import Path

from job_scraper.core.db import JobRepository
from job_scraper.core.filters import apply_dedup, is_excluded
from job_scraper.core.markdown_export import screenshot_relpath, stem_for, write
from job_scraper.core.raw_export import write as write_raw
from job_scraper.core.robots import robots_allowed
from job_scraper.core.screenshots import capture_element
from job_scraper.sites.base import FetchStrategy, SiteAdapter, fetch_page
from job_scraper.sites.registry import SITE_REGISTRY


def run_site(
    adapter: SiteAdapter,
    repo: JobRepository,
    jobs_dir: str,
    run_started_at: str,
    raw_dir: str | None = None,
    screenshots_dir: str | None = None,
) -> dict:
    """For each ListingStub from adapter.list_postings(): fetch its detail
    page via fetch_page(adapter.fetch_strategy, stub.detail_url); if
    raw_dir is set, save the raw fetched bytes via raw_export.write(
    posting, page, raw_dir) unconditionally (before exclusion/dedup), so
    the raw page is captured regardless of downstream filtering — that
    filtering logic can change later and raw storage shouldn't have to be
    re-scraped to catch up. Then call adapter.parse_detail(stub, page),
    then: if is_excluded(posting): skip (don't store markdown).
    Otherwise: posting, dup_id = apply_dedup(posting, repo); changed =
    repo.upsert(posting, seen_at=run_started_at); if dup_id is not None:
    repo.set_duplicate_of(posting.site_id, posting.listing_id, dup_id) —
    and do NOT export markdown for a duplicate, regardless of `changed`.
    If not a duplicate and changed: call markdown_export.write(posting,
    jobs_dir). After the loop, call
    repo.mark_stale_not_seen_since(adapter.site_id, run_started_at).
    Returns a dict of counters: {"seen": int, "excluded": int,
    "duplicates": int, "written": int, "stale_marked": int}."""
    counters = {
        "seen": 0,
        "excluded": 0,
        "duplicates": 0,
        "written": 0,
        "stale_marked": 0,
        "screenshots_taken": 0,
        "screenshots_failed": 0,
    }

    for stub in adapter.list_postings():
        counters["seen"] += 1
        page = fetch_page(adapter.fetch_strategy, stub.detail_url)
        posting = adapter.parse_detail(stub, page)

        if raw_dir:
            write_raw(posting, page, raw_dir, ext=adapter.raw_format)

        if is_excluded(posting):
            counters["excluded"] += 1
            continue

        posting, dup_id = apply_dedup(posting, repo)
        changed = repo.upsert(posting, seen_at=run_started_at)

        if dup_id is not None:
            repo.set_duplicate_of(posting.site_id, posting.listing_id, dup_id)
            counters["duplicates"] += 1
        elif changed:
            screenshot = None
            if screenshots_dir and adapter.screenshot_selector:
                stem = stem_for(posting)
                out_path = Path(screenshots_dir) / f"{stem}.png"
                try:
                    ok = capture_element(
                        posting.source_url,
                        adapter.screenshot_selector,
                        str(out_path),
                        stealth=adapter.fetch_strategy == FetchStrategy.STEALTH,
                    )
                except Exception as exc:
                    print(f"Warning: screenshot failed for {stem}: {exc}", file=sys.stderr)
                    ok = False
                if ok:
                    counters["screenshots_taken"] += 1
                else:
                    counters["screenshots_failed"] += 1
                if ok or out_path.exists():
                    screenshot = screenshot_relpath(stem)
            write(posting, jobs_dir, screenshot=screenshot)
            counters["written"] += 1

    stale_count = repo.mark_stale_not_seen_since(adapter.site_id, run_started_at)
    counters["stale_marked"] = stale_count

    return counters


def run(
    site_ids: list[str],
    repo: JobRepository,
    jobs_dir: str,
    ignore_robots: bool = False,
    raw_dir: str | None = None,
    screenshots_dir: str | None = None,
) -> dict[str, dict]:
    """For each site_id: if not in SITE_REGISTRY, skip with a printed
    warning (to stderr) and continue. If robots_allowed(adapter.base_url) is
    False, skip with a printed warning and continue — unless ignore_robots
    is True, in which case the check is bypassed (with a printed notice, so
    the bypass is always visible in the run's output, not silent). Otherwise
    instantiate the adapter and call run_site(..., raw_dir=raw_dir). Returns
    {site_id: counters_dict} for every site actually run."""
    results = {}

    for site_id in site_ids:
        if site_id not in SITE_REGISTRY:
            print(f"Warning: Site {site_id} not found in registry", file=sys.stderr)
            continue

        adapter_class = SITE_REGISTRY[site_id]
        adapter = adapter_class()

        if not robots_allowed(adapter.base_url):
            if ignore_robots:
                print(
                    f"Notice: robots.txt disallows scraping {adapter.base_url}, "
                    "but --ignore-robots was set; proceeding anyway",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Warning: robots.txt disallows scraping {adapter.base_url}",
                    file=sys.stderr,
                )
                continue

        run_started_at = datetime.now().isoformat()
        counters = run_site(
            adapter,
            repo,
            jobs_dir,
            run_started_at,
            raw_dir=raw_dir,
            screenshots_dir=screenshots_dir,
        )
        results[site_id] = counters

    return results
