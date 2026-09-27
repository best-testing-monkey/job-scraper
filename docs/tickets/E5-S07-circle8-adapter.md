# E5-S07: Circle8 site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`,
`E1-S01`, and the `base.py` STEALTH support (already merged). Style
reference: `job_scraper/sites/pro_act.py` for class shape, and
`job_scraper/sites/sevenstars.py` if it already exists when you start this
story (same vendor template, similar markup, but NOT identical — see
notes below, don't just copy it blindly).

## Goal

A `SiteAdapter` for circle8.nl (`site_id = "circle8"`,
`base_url = "https://www.circle8.nl"`, `fetch_strategy =
FetchStrategy.STEALTH` — same Vercel WAF situation as sevenstars.nl,
explicit site-owner permission obtained, `fetch_page` already handles the
STEALTH dispatch).

**Known, accepted scope limit: page 1 only (~10 of ~70 postings).**
circle8's listing pagination is JS-button-driven (`<button>` elements with
no `href`, no `data-page`, no `?page=` URL pattern anywhere in the fetched
HTML — confirmed by DOM inspection, unlike sevenstars' real `?page=N`
links). Following it would need either simulating a real click via
StealthyFetcher's page-interaction hooks, or reverse-engineering whatever
API call the button triggers — neither was investigated during
reconnaissance and both are a meaningfully bigger task than this ticket.
**Don't attempt pagination for this adapter** — implement page-1-only,
document the gap the same way `headfirst`'s partial coverage is
documented (a `scrape_note` on every posting, or a one-line README
mention — check how `E5-S05`'s headfirst ticket phrased its scope-limit
note and match that style).

## Context

Create: `job_scraper/sites/circle8.py`, `tests/test_circle8.py`.

Fixtures (read-only, real data fetched via StealthyFetcher):
- `tests/fixtures/circle8/listing.html` — real listing, page 1 of 7
- `tests/fixtures/circle8/detail_VNR-85422.html` — real detail page
  ("Adviseur GGD-GHOR")

`fetch_page` returns raw bytes; `BeautifulSoup(page, "html.parser")`
accepts bytes directly.

## Listing: `LISTING_URL = "https://www.circle8.nl/opdrachten"`

Same card class as sevenstars, `.c-vacancy-grid-card` (10 per page, this
adapter only reads page 1). Per card:
- title: `.c-vacancy-grid-card__title` text
- detail URL: `a[href^="/opdracht/"]`, relative, join with `self.base_url`
- `listing_id`: parse from the href's trailing slug segment after the
  last underscore, e.g. `/opdracht/adviseur-ggd-ghor_VNR-85422` →
  `"VNR-85422"` (same regex approach as sevenstars: `r"_([A-Za-z0-9-]+)$"`
  on the URL path)

## Detail page — prefer JSON-LD (`script[type="application/ld+json"]`,
object with `"@type": "JobPosting"`), same as sevenstars, but **circle8's
JSON-LD description is already plain text (HTML tags NOT retained) —
unlike sevenstars where description keeps HTML tags. Check the real
fixture before assuming either way; don't strip tags that aren't there.**

```
JobPosting.title                                  -> title
JobPosting.description                             -> description
JobPosting.datePosted                              -> posted_date
JobPosting.validThrough                            -> extra_fields["validThrough"]
JobPosting.jobLocation.address.addressLocality     -> location
JobPosting.hiringOrganization.name                 -> client (circle8
    DOES publish the real end client here, e.g. "ICTU Perceel 2 -
    Projectmanagement & Consultancy (KWIV 1, 4 en 5)" — unlike
    sevenstars, this is safe/expected to use)
JobPosting.industry                                -> category (this is
    meaningfully descriptive on circle8, e.g. "Openbaar bestuur en
    overheidsdiensten" — unlike sevenstars where it was just "Other")
```

Hours and duration are NOT in JSON-LD — circle8's hero usp markup is
**plain `<div>` elements, not `<h5 class="...usp-value">` like
sevenstars** (same top-level class names, different sub-markup — don't
assume the two sites share a selector here). Selector:
`.c-vacancy-hero__usp-container .c-vacancy-hero__usp div:not(.c-vacancy-hero__usp-icon)`,
yielding a list of 5 text values in order: location, duration, hours,
start date, deadline. Real example: `["Utrecht", "12 maand(en)",
"8  Uren per week", "Start: 15-10-2026", "Deadline: 29-9-2026"]`. Index 1
→ `duration`, index 2 → `hours`. (Index 3/4 have inline "Start:"/
"Deadline:" labels already in the text — keep them as-is or strip the
label, your choice, just be consistent.)

`rate`: JSON-LD `baseSalary.value` — same as sevenstars, expect this to
often be empty/`None`; not a bug if so.

## Acceptance criteria

- `Circle8Adapter.site_id == "circle8"`, `fetch_strategy ==
  FetchStrategy.STEALTH`.
- `list_postings()` given the listing fixture yields the page-1 postings
  only, including one with `listing_id == "VNR-85422"` — no pagination
  attempted.
- `parse_detail()` given the detail fixture returns a `JobPosting` with
  `title == "Adviseur GGD-GHOR"`, `listing_id == "VNR-85422"`,
  `site_id == "circle8"`, `location == "Utrecht"`,
  `client` containing `"ICTU"`, `category` containing `"Openbaar bestuur"`,
  `hours` containing `"8"`, `duration` containing `"12"`, non-empty
  `description`.
- Every `JobPosting` from this adapter has a `scrape_note` mentioning the
  page-1-only limitation.
- No live network calls in tests.

## Definition of done

Per Appendix A.
