# E5-S09: Extend integration test and README for second-wave sites

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E5-S08`
(all 10 sites registered).

## Goal

Extend the existing end-to-end integration test and README to cover the 7
new sites, following the same fixture-driven pattern already used for the
first 3.

## Context

Modify: `tests/test_integration.py`, `README.md`.
Read (do not modify): the existing `FixtureAwareProActAdapter` /
`FixtureAwareHeroAdapter` / `FixtureAwareFlexValueAdapter` wrapper classes
and `fixture_fetch_page` fixture already in `tests/test_integration.py`,
for the pattern to extend. Also read each new adapter's own test file
(`tests/test_synprofs.py`, etc.) for how each one's fixtures are loaded.

## What to do

1. For each of the 7 new adapters, add a `FixtureAware<Site>Adapter`
   wrapper subclass (same pattern as the existing 3: override
   `list_postings()` to filter down to the one listing_id that has a
   saved detail fixture — for `synprofs`/`harveynash`, that's whatever
   `listing_id` matches their one saved `detail_*.html` fixture; for
   `stone_interim`/`tender_link`, note their `list_postings()` already
   returns full records without needing a separate detail fetch in some
   cases — check each adapter's actual implementation and adapt the
   wrapper accordingly rather than assuming they all work like Pro-Act).
2. Extend `fixture_fetch_page` to dispatch on each new site's
   `LISTING_URL` and detail URL patterns, returning the right fixture
   bytes (`Path(...).read_bytes()`, not `.read_text()`, since `fetch_page`
   now returns bytes — see `job_scraper/sites/base.py`).
3. For `stone_interim` specifically: its `list_postings()` calls
   `Fetcher.post` directly, not `fetch_page` — the integration test needs
   an additional `patch("job_scraper.sites.stone_interim.Fetcher.post", ...)`
   (or whatever the adapter actually imports — check the file), separate
   from the `fetch_page` patches used for everything else.
4. Add all 7 new site ids to the `run([...], repo, jobs_dir)` calls (both
   the first and second run, for the idempotence check) alongside the
   existing 3.
5. Update `README.md`'s "Currently supported sites" list to include all
   10, and add a short note next to `headfirst` that it only surfaces a
   partial set of postings with no full description (per its own ticket's
   documented scope limits) — don't repeat the whole limitation, just a
   one-line pointer.

## Acceptance criteria

- `uv run pytest tests/ -q` passes, full suite, all 10 sites' postings
  written in the integration test's first run, `written == 0` for all 10
  on the second (idempotent) run.
- `uv run python -m job_scraper list-sites` (live, not mocked) prints all
  10 site ids.
- README accurately lists all 10 supported sites.

## Definition of done

Per Appendix A. This is the last story in the second wave — after this,
run the full suite and confirm everything passes together before
committing.
