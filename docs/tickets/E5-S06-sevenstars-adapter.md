# E5-S06: Sevenstars site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`,
`E1-S01`, and the `base.py` STEALTH support (already merged — see
`job_scraper/sites/base.py`'s `fetch_page`, which now handles
`FetchStrategy.STEALTH` via `StealthyFetcher`). Style reference:
`job_scraper/sites/pro_act.py` for class shape.

## Goal

A `SiteAdapter` for sevenstars.nl (`site_id = "sevenstars"`,
`base_url = "https://www.sevenstars.nl"`, `fetch_strategy =
FetchStrategy.STEALTH` — this site is behind a Vercel bot-mitigation WAF
that returns HTTP 429 to plain HTTP; only a real browser (Scrapling's
`StealthyFetcher`) gets through. We have explicit permission from the site
owner to scrape it; `fetch_page` already handles the STEALTH dispatch, you
don't need to call `StealthyFetcher` directly). **Includes pagination**
(confirmed real, only 2 pages currently).

## Context

Create: `job_scraper/sites/sevenstars.py`, `tests/test_sevenstars.py`.

Fixtures (read-only, real data fetched via StealthyFetcher):
- `tests/fixtures/sevenstars/listing.html` — real listing, page 1 of 2
- `tests/fixtures/sevenstars/detail_7S-004982.html` — real detail page
  ("Agile Coach")

`fetch_page` returns raw bytes; `BeautifulSoup(page, "html.parser")`
accepts bytes directly.

## Listing: `LISTING_URL = "https://www.sevenstars.nl/opdrachten"`

Card selector: `.c-vacancy-grid-card` (10 per page). Per card:
- title: `.c-vacancy-grid-card__title` text
- detail URL: `a[href^="/opdracht/"]` inside
  `.c-vacancy-grid-card__header--left`, `href` — relative, join with
  `self.base_url`
- `listing_id`: parse from the href's trailing slug segment after the
  last underscore, e.g. `/opdracht/agilecoach_7S-004982` → `"7S-004982"`
  (regex `r"_([A-Za-z0-9-]+)$"` on the URL path)

**Pagination**: `.c-lister-pagination__wrapper` has real page links.
After parsing page 1 (`LISTING_URL`), check for a next-page link (e.g.
`.c-lister-pagination__page-control--next[data-disabled="false"]`, `href`
attribute e.g. `?page=2`); if present and not disabled, fetch
`f"{self.LISTING_URL}{href}"` (or urljoin, since `href` may be
`?page=2` — join relative to `LISTING_URL`) via `fetch_page` again and
parse it the same way, continuing until no next-page link or it's marked
disabled. In practice this is currently just 2 pages, but implement the
loop generically (don't hardcode "fetch page 2 once") so it keeps working
if more postings appear later.

## Detail page — **prefer the JSON-LD block** over site-specific CSS
classes (`script[type="application/ld+json"]`, take the object with
`"@type": "JobPosting"`, `json.loads` its text):

```
JobPosting.title                                  -> title
JobPosting.description  (HTML — strip tags)        -> description
JobPosting.datePosted                              -> posted_date
JobPosting.validThrough                            -> extra_fields["validThrough"]
JobPosting.jobLocation.address.addressLocality     -> location
```

Hours and duration are NOT in JSON-LD on this site — use
`.c-vacancy-hero__usp-value` (a list of 4 `<h5>` elements on the detail
page): index 2 (0-based) is hours (e.g. `"40 uren"`), index 1 is duration
(e.g. `"3 Maanden"`).

**`client` and `category`: deliberately leave both `None` for this
adapter.** JSON-LD's `hiringOrganization.name` is just `"Seven Stars"`
(the agency itself, not the end client) — the real end client is only
present in unstable internal framework state, not a public/stable field,
and this site appears to conceal it by design. Don't attempt to extract
it from internal script blobs.

`rate`: JSON-LD `baseSalary.value` — check `MinValue`/`MaxValue` if
populated (format as e.g. `f"{min}-{max}"`); on the sample fixture these
were empty strings, so `rate` will legitimately be `None` for it — that's
expected, not a bug.

## Acceptance criteria

- `SevenstarsAdapter.site_id == "sevenstars"`, `fetch_strategy ==
  FetchStrategy.STEALTH`.
- `list_postings()`, with `fetch_page` mocked to return the page-1 fixture
  on the first call and (for the pagination test) a small synthetic
  "page 2 has no next link" HTML snippet on a second call, yields at least
  the postings from page 1 including one with `listing_id == "7S-004982"`,
  and stops cleanly when no next-page link is found (doesn't loop forever
  or error).
- `parse_detail()` given the detail fixture returns a `JobPosting` with
  `title == "Agile Coach"`, `listing_id == "7S-004982"`,
  `site_id == "sevenstars"`, `location == "Zwolle"`, `hours == "40 uren"`,
  `duration == "3 Maanden"`, `client is None`, `category is None`,
  non-empty `description`.
- No live network calls in tests (mock `fetch_page`, not
  `StealthyFetcher` directly, so the test doesn't care which strategy is
  configured).

## Definition of done

Per Appendix A.
