# E6-S09: Working Nomads site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`. Style reference: `job_scraper/sites/tender_link.py` (JSON API, no separate detail fetch needed).

## Goal

`site_id = "working_nomads"`, `base_url = "https://www.workingnomads.com"`, `fetch_strategy = FetchStrategy.STATIC` — despite this site's human-facing pages being an AngularJS SPA, it has a genuine **public, unauthenticated JSON API** at `https://www.workingnomads.com/api/exposed_jobs/` (linked from the site's own footer) that returns all currently-active jobs directly — no browser needed at all. `LISTING_URL = "https://www.workingnomads.com/api/exposed_jobs/"`.

## Context

Create: `job_scraper/sites/working_nomads.py`, `tests/test_working_nomads.py`.

**No fixture exists yet for this adapter** (reconnaissance verified the API live via curl but didn't save a JSON fixture file). Before writing tests, fetch a real sample yourself: `curl -s https://www.workingnomads.com/api/exposed_jobs/ -o /tmp/wn.json` then inspect it, filter to a handful of QA/test-relevant records (check the `tags` field for "qa"/"test"/"playwright"/"selenium"/"cypress" — reconnaissance found `category_name` is unreliable for relevance, e.g. a real QA job was miscategorized as "Administration", so filter on `tags` instead), and save a trimmed JSON array (5-10 real records is enough) to `tests/fixtures/working_nomads/listing.json`. Keep the records byte-real from the live API, just reduce the array length — don't fabricate or hand-edit field values.

`fetch_page` returns raw bytes; `json.loads(page)` accepts bytes directly.

## Fields (per record in the API's JSON array — verified real keys)

```
url                -> use as detail_url / source_url (already absolute); derive
                      listing_id from its trailing slug or hash it — check
                      what's actually unique per record in your fixture
title              -> title
description        -> description (HTML — strip tags)
company_name       -> client
category_name      -> extra_fields["category_name"] (documented as unreliable
                      for relevance — don't map it to the `category` field)
tags               -> category (comma-separated string in the source; use
                      as-is or reformat, your choice, just don't drop it)
location           -> location
pub_date           -> posted_date
```

Since the whole record is already present from the single API call, `parse_detail()` should NOT make a second fetch — cache records during `list_postings()` (same pattern as `tender_link.py`) and have `parse_detail(stub, page)` look up by `listing_id`, ignoring `page`.

`rate`/`hours`/`duration` do not exist in this API's schema — leave all three `None` always.

## Acceptance criteria

- `WorkingNomadsAdapter.site_id == "working_nomads"`, `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` on the fixture yields one stub per record in your trimmed JSON array.
- `parse_detail()` for at least one record returns matching real field values from your own fixture (title, client, location, category containing a QA-relevant tag, non-empty description) — assert against whatever real values you captured, not invented ones.
- No live network calls in the test itself (only your fixture-creation step touched the network, and that's not part of the test suite).

## Definition of done

Per Appendix A.
