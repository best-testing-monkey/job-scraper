# E6-S12: Extend integration test and README for third-wave sites

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E6-S11` (all 20 sites registered).

## Goal

Extend the existing end-to-end integration test and README to cover the 10 new sites, following the same fixture-driven pattern already used for the first 10.

## Context

Modify: `tests/test_integration.py`, `README.md`.
Read (do not modify): the existing `FixtureAware<Site>Adapter` wrapper classes and `fixture_fetch_page` fixture already in `tests/test_integration.py` (there are 10 examples to follow — including `FixtureAwareStoneInterimAdapter`'s special-cased `Fetcher.post` patch and `FixtureAwareTenderLinkAdapter`'s cache-based no-second-fetch pattern, both relevant precedents here too). Also read each of the 10 new adapters' own test files for their real fetch mechanics — some (`working_nomads`) cache records like `tender_link` does; some (`guru`) use STEALTH; `ictergezocht` calls `fetch_page` with extra kwargs (`solve_cloudflare=True`) that the test's mock needs to accept and ignore.

## What to do

1. For each of the 10 new adapters, add a `FixtureAware<Site>Adapter` wrapper subclass filtering `list_postings()` down to the one listing_id with a saved detail fixture (skip this for `arc_dev`, which already has only one real posting — no filtering needed there).
2. Extend `fixture_fetch_page` to dispatch on each new site's `LISTING_URL`/detail-URL patterns, returning the right fixture bytes.
3. Handle adapter-specific fetch signatures: your mock for `fetch_page` needs to accept `**kwargs` (for `ictergezocht`'s `solve_cloudflare=True` call) without erroring, even though the mock ignores them.
4. Add all 10 new site ids to the `run([...], repo, jobs_dir)` calls (both runs, idempotence check) alongside the existing 10.
5. Update `README.md`'s "Currently supported sites" list to all 20, with a one-line pointer for each site that has a documented partial-coverage/gated-field limitation (`arc_dev` no pagination, `guru` needs STEALTH due to live bot-blocking, `planet_interim`/`wearedevelopers`/`ictergezocht`/`freelancermap` page-1-only or gated-fields — check each adapter's own `scrape_note` for the exact wording rather than re-deriving it).

## Acceptance criteria

- `uv run pytest tests/ -q` passes, full suite, all 20 sites' postings written in the integration test's first run, `written == 0` for all 20 on the second (idempotent) run.
- `uv run python -m job_scraper list-sites` (live, not mocked) prints all 20 site ids.
- README accurately lists all 20 supported sites.

## Definition of done

Per Appendix A. This is the last story in this wave — after this, run the full suite and confirm everything passes together before committing.
