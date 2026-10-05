from job_scraper.core.db import JobRepository
from job_scraper.core.markdown_export import md_path_for, set_stale_line


def sync_stale_markers(repo: JobRepository, jobs_dir: str, today: str) -> dict[str, int]:
    """Bring every markdown file in line with the DB's stale state.

    Stale rows without a date are dated `today` (stored in the DB); stale rows
    get '- Stale since:' written, live rows get it removed. Idempotent."""
    counters = {"stale_rows": 0, "dated": 0, "written": 0, "cleared": 0, "missing_md": 0}

    for site_id, listing_id, title, is_stale, stale_since in repo.list_stale_state():
        if is_stale == 1:
            counters["stale_rows"] += 1

        md = md_path_for(jobs_dir, site_id, listing_id, title)
        if not md.exists():
            counters["missing_md"] += 1
            continue

        if is_stale == 1:
            if stale_since is None:
                repo.set_stale_since(site_id, listing_id, today)
                stale_since = today
                counters["dated"] += 1
            if set_stale_line(str(md), stale_since):
                counters["written"] += 1
        elif set_stale_line(str(md), None):
            counters["cleared"] += 1

    return counters
