# E6-S05: Guru site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`, and the `base.py` STEALTH support (already merged). Style reference: `job_scraper/sites/sevenstars.py` (STEALTH + real pagination).

## Goal

`site_id = "guru"`, `base_url = "https://www.guru.com"`, `fetch_strategy = FetchStrategy.STEALTH`. **Use STEALTH even though the selectors below were derived from static HTML** — guru.com is currently blocked site-wide by Incapsula bot-protection for plain HTTP (verified: HTTP 403 on every path including `/robots.txt`, during reconnaissance). This is the same class of problem `StealthyFetcher` already solves for `sevenstars`/`circle8`. `LISTING_URL = "https://www.guru.com/d/jobs/"`.

## Context

Create: `job_scraper/sites/guru.py`, `tests/test_guru.py`.
Fixtures (read-only — these came from Wayback Machine archive snapshots of the real site, since live fetch was blocked during reconnaissance; the HTML structure is real, not fabricated):
- `tests/fixtures/guru/listing.html`
- `tests/fixtures/guru/detail_2101732.html`

## Listing

Card: `div.record.jobRecord[data-gid]` — `data-gid` is the numeric `listing_id` directly (no URL parsing needed). Title + detail URL: `h2.jobRecord__title a` (href format `/jobs/<slug>/<id>&SearchUrl=...` — **strip everything from `&SearchUrl` onward** to get the clean detail path).

**Pagination**: real, server-rendered — `ul#ctl00_guB_ulpaginate` with real `<a href="/d/jobs/pg/N/">` links (page 1 has no `/pg/1/` suffix, it's the bare `LISTING_URL`). Implement generically, following the "next" control until absent.

## Detail

```
h1.jobHeading__title                    -> title
div.jobHeading__budget                  -> rate (full text, e.g. "Fixed Price | $250-$500 | India" —
                                            also often contains a trailing location; leave the
                                            whole string as rate, don't try to split it)
p.jobHeading__meta                      -> posted_date (leading "Posted ..." text, relative only) and
                                            listing_id cross-check via literal "Job ID: <digits>" text
div.jobDetails__category p              -> category (two-level text, e.g.
                                            "Programming & Development" > "QA & Testing" — keep as one string)
a.skillsList__skill                     -> join all into extra_fields["skills"]
pre.jobDetails__description             -> description — MUST strip the trailing
                                            " ... <a href='/login.aspx?...'>Show more</a>" boilerplate,
                                            it's decorative on every posting, not real truncation
```

`client` does not exist on this site's logged-out detail view — verified absent on multiple postings, leave `None` always. `duration`/`hours` only appear on HOURLY listings' budget block on the listing page (not detail) — this fixture is a fixed-price posting, so both are legitimately absent; leave `None` when not found rather than guessing.

## Acceptance criteria

- `GuruAdapter.site_id == "guru"`, `fetch_strategy == FetchStrategy.STEALTH`.
- `list_postings()` on the fixture yields real stubs, one with `listing_id == "2101732"` (or matching whatever real id the detail fixture corresponds to — verify against the fixture rather than assuming).
- `parse_detail()` returns `title == "Automation Test Selenium with C#"`, `rate` containing `"250-$500"` (or equivalent formatting), `category` containing `"QA"` or `"Testing"`, `client is None`, non-empty `description` with no `"Show more"` suffix left in it.

## Definition of done

Per Appendix A.
