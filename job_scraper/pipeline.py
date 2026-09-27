from datetime import datetime

from job_scraper.core.db import JobRepository
from job_scraper.core.filters import apply_dedup, is_excluded
from job_scraper.core.markdown_export import write
from job_scraper.core.robots import robots_allowed
from job_scraper.sites.base import FetchStrategy, SiteAdapter, fetch_page
from job_scraper.sites.registry import SITE_REGISTRY


def run_site(
    adapter: SiteAdapter, repo: JobRepository, jobs_dir: str, run_started_at: str
) -> dict:
    """For each ListingStub from adapter.list_postings(): fetch its detail
    page via fetch_page(adapter.fetch_strategy, stub.detail_url), call
    adapter.parse_detail(stub, page), then: if is_excluded(posting): skip
    (don't store). Otherwise: posting, dup_id = apply_dedup(posting, repo);
    changed = repo.upsert(posting, seen_at=run_started_at); if dup_id is
    not None: repo.set_duplicate_of(posting.site_id, posting.listing_id,
    dup_id) — and do NOT export markdown for a duplicate, regardless of
    `changed`. If not a duplicate and changed: call
    markdown_export.write(posting, jobs_dir). After the loop, call
    repo.mark_stale_not_seen_since(adapter.site_id, run_started_at).
    Returns a dict of counters: {"seen": int, "excluded": int,
    "duplicates": int, "written": int, "stale_marked": int}."""
    counters = {"seen": 0, "excluded": 0, "duplicates": 0, "written": 0, "stale_marked": 0}

    for stub in adapter.list_postings():
        counters["seen"] += 1
        page = fetch_page(adapter.fetch_strategy, stub.detail_url)
        posting = adapter.parse_detail(stub, page)

        if is_excluded(posting):
            counters["excluded"] += 1
            continue

        posting, dup_id = apply_dedup(posting, repo)
        changed = repo.upsert(posting, seen_at=run_started_at)

        if dup_id is not None:
            repo.set_duplicate_of(posting.site_id, posting.listing_id, dup_id)
            counters["duplicates"] += 1
        elif changed:
            write(posting, jobs_dir)
            counters["written"] += 1

    stale_count = repo.mark_stale_not_seen_since(adapter.site_id, run_started_at)
    counters["stale_marked"] = stale_count

    return counters


def run(site_ids: list[str], repo: JobRepository, jobs_dir: str) -> dict[str, dict]:
    """For each site_id: if not in SITE_REGISTRY, skip with a printed
    warning (to stderr) and continue. If robots_allowed(adapter.base_url) is
    False, skip with a printed warning and continue. Otherwise instantiate
    the adapter and call run_site(...). Returns {site_id: counters_dict}
    for every site actually run."""
    import sys

    results = {}

    for site_id in site_ids:
        if site_id not in SITE_REGISTRY:
            print(f"Warning: Site {site_id} not found in registry", file=sys.stderr)
            continue

        adapter_class = SITE_REGISTRY[site_id]
        adapter = adapter_class()

        if not robots_allowed(adapter.base_url):
            print(
                f"Warning: robots.txt disallows scraping {adapter.base_url}",
                file=sys.stderr,
            )
            continue

        run_started_at = datetime.now().isoformat()
        counters = run_site(adapter, repo, jobs_dir, run_started_at)
        results[site_id] = counters

    return results
