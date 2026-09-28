# E6-S07: ICTerGezocht site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`, STEALTH support. Style reference: `job_scraper/sites/circle8.py`.

## Goal

`site_id = "ictergezocht"`, `base_url = "https://www.ictergezocht.nl"`, `fetch_strategy = FetchStrategy.STEALTH`, `LISTING_URL = "https://www.ictergezocht.nl/ict-vacatures/"` (not `/vacatures` — that path doesn't exist on this site).

**Important**: this site fronts a Cloudflare JS challenge. `fetch_page` (in `job_scraper/sites/base.py`) now accepts extra kwargs that pass straight through to the underlying fetcher — call it as
`fetch_page(self.fetch_strategy, url, solve_cloudflare=True, network_idle=True)`
for every fetch this adapter makes (both listing and detail).

**Known, accepted scope limit**: pagination looks real (`?page=2` etc.) but is confirmed non-functional — every page number silently returns page-1 content unchanged. **Page 1 only** (documented via `scrape_note`), same limitation category as `circle8`/`arc_dev`.

## Context

Create: `job_scraper/sites/ictergezocht.py`, `tests/test_ictergezocht.py`.
Fixtures: `tests/fixtures/ictergezocht/listing.html`, `tests/fixtures/ictergezocht/detail_438712.html`.

## Listing

Card: `section.component-card.feed-card` — has real `data-*` attributes: `data-vacancyid` (= `listing_id` directly), `data-business` (client), `data-hours`, `data-location-label`, `data-contract-type`. Title + URL: `h3 a.feed-card__link`.

## Detail (fully public, no login wall for these fields — confirmed)

```
.vacancy-title-heading (or h1.mb-7 on mobile layout — try both)   -> title
.vacancy-company-meta .logo-title span (first span)               -> client
.component-location span (first child)                            -> location
.hero-oneliners .component-list-list div                          -> category (join all)
.vacancy-benefits .component-spec whose icon has
  aria-label containing "uur"        -> .spec-value                -> hours
.vacancy-benefits .component-spec whose icon class contains
  "currency-euro-circle"             -> .spec-value                -> rate
.vacancy-benefits .component-spec whose icon class contains
  "briefcase-02"                     -> .spec-value                -> extra_fields["contract_type"]
  (e.g. "Loondienst (vast)" vs freelance/interim — useful signal,
  not a dedicated JobPosting field)
.vacancy-text .vacancy-description-text.vacancy-full-text-dom      -> description (full, ungated)
```

`posted_date` and `duration` do not exist as real fields on the detail page (only a relative freshness tag on the LISTING card, not carried to detail) — leave both `None` always for this adapter.

## Acceptance criteria

- `IctergezochtAdapter.site_id == "ictergezocht"`, `fetch_strategy == FetchStrategy.STEALTH`.
- `list_postings()` on the fixture yields real stubs (page 1 only, ~50), one with `listing_id == "438712"`.
- `parse_detail()` returns `title` containing `"Functioneel Beheerder"`, `client == "Concretor"`, `location == "Barendrecht"`, `hours` containing `"36"`, non-empty `description`, `posted_date is None`, `duration is None`, non-empty `scrape_note` mentioning the pagination limitation.

## Definition of done

Per Appendix A.
