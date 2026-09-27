# E2-S04: Pipeline orchestration and CLI entrypoint

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E1-S02`
(`JobRepository`), `E1-S03` (`markdown_export`), `E2-S01` (`robots_allowed`),
`E2-S02` (`is_excluded`, `apply_dedup`), `E2-S03` (`SiteAdapter`,
`FetchStrategy`, `SITE_REGISTRY`).

Note: `SITE_REGISTRY` is still empty when you implement this (real adapters
land in Epic 3, registered in `E3-S05`). Write and test this story entirely
against a fake/stub `SiteAdapter` you define in the test file — do not wait
for real adapters to exist.

## Goal

Wire the pieces from Epics 1-2 into one orchestration function per site, and
a CLI that invokes it.

## Context

Create: `job_scraper/pipeline.py`, `job_scraper/cli.py`, `tests/test_pipeline.py`.

Import from `job_scraper.core.models`, `job_scraper.core.db`,
`job_scraper.core.markdown_export`, `job_scraper.core.robots`,
`job_scraper.core.filters`, `job_scraper.sites.base`,
`job_scraper.sites.registry`.

## `job_scraper/pipeline.py`

```python
def fetch_page(strategy: FetchStrategy, url: str) -> Any:
    """Dispatches to the right Scrapling fetcher for this strategy.
    FetchStrategy.STATIC -> scrapling.fetchers.Fetcher.get(url). The other
    two strategies (STEALTH, DYNAMIC) are out of scope this phase: raise
    NotImplementedError with a message naming the strategy if called."""

def run_site(adapter: SiteAdapter, repo: JobRepository, jobs_dir: str, run_started_at: str) -> dict:
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

def run(site_ids: list[str], repo: JobRepository, jobs_dir: str) -> dict[str, dict]:
    """For each site_id: if not in SITE_REGISTRY, skip with a printed
    warning (to stderr) and continue. If robots_allowed(adapter.base_url) is
    False, skip with a printed warning and continue. Otherwise instantiate
    the adapter and call run_site(...). Returns {site_id: counters_dict}
    for every site actually run."""
```

## `job_scraper/cli.py`

```
python -m job_scraper scrape --site <site-id> [--site <site-id> ...] | --site all [--db PATH] [--jobs-dir PATH]
python -m job_scraper list-sites
```

- `scrape`: `--site` may be repeated, or given once as `all` (meaning every
  key in `SITE_REGISTRY`). Defaults: `--db scraper.db`, `--jobs-dir jobs/`.
  Constructs a `JobRepository(db_path)`, calls `pipeline.run(site_ids, repo,
  jobs_dir)`, prints the returned counters dict per site to stdout.
- `list-sites`: prints each `site_id` in `SITE_REGISTRY` (one per line, sorted).
- Use stdlib `argparse`.

## Acceptance criteria

- `tests/test_pipeline.py` defines a fake `SiteAdapter` subclass (fixed
  `site_id`, `fetch_strategy = FetchStrategy.STATIC`) whose
  `list_postings()` yields 2-3 hardcoded `ListingStub`s and whose
  `parse_detail()` returns a hardcoded `JobPosting` per stub (ignoring the
  `page` argument entirely — no real fetching in this test). Monkeypatch
  `job_scraper.pipeline.fetch_page` to return `None` (or any placeholder)
  so `parse_detail` never needs real HTML.
- Test `run_site` with that fake adapter and a temp `JobRepository`/`tmp_path`
  jobs dir: confirms the counters dict has the right `"seen"` count,
  confirms `.md` files were written under the jobs dir for non-duplicate,
  non-excluded postings, confirms a posting whose fake description contains
  an exclusion keyword is NOT written and increments `"excluded"`.
- Test `run` with `SITE_REGISTRY` monkeypatched (in the test only) to
  contain the fake adapter: confirms an unknown site_id is skipped without
  raising, confirms `robots_allowed` being monkeypatched to `False` causes
  the site to be skipped (0 postings processed) without raising.
- `python -m job_scraper list-sites` (via `uv run python -m job_scraper
  list-sites`) exits 0 (empty output is fine — registry is empty until
  Epic 3 lands).

## Definition of done

Per Appendix A.
