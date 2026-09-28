# E6-S01: IamExpat Jobs site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`. Style reference: `job_scraper/sites/pro_act.py`.

## Goal

`site_id = "iamexpat"`, `base_url = "https://www.iamexpat.nl"`, `fetch_strategy = FetchStrategy.STATIC`, `LISTING_URL = "https://www.iamexpat.nl/career/jobs-netherlands"` (no separate IT filter exists — it redirects here).

## Context

Create: `job_scraper/sites/iamexpat.py`, `tests/test_iamexpat.py`.
Fixtures: `tests/fixtures/iamexpat/listing.html`, `tests/fixtures/iamexpat/detail_tLJWUBCWY1P8MBXMScbwRE.html`.

## Listing

Card/link: `a[class*="JobBoardItemCard_cardWrapper"]` (use a substring match, not the full hashed class — Next.js CSS-module hashes change on redeploy). `href` = relative detail URL; `listing_id` = trailing path segment. Title: `span.title-7` inside the link.

**Pagination**: real, confirmed working — `?page=N` query param on `LISTING_URL`, increment from 1 until a page returns no cards (confirmed via a real fetch that `?page=2` gives a different set of postings). Implement the loop generically like `sevenstars.py` does.

## Detail

```
h1.title-3                                          -> title
img.BodyTop_logo__YKhP5 [alt attribute]              -> client
last button.breadcrumbs-text before the final        -> category
  non-clickable span, inside .Breadcrumb_scrollbarHidden__NZJMQ
div.BodyTop_specs__8gRFr div.BodyTop_specsItem__FPzGn  -> 5 positional items:
  [0] location, [1] duration/employment-type, [2] hours,
  (indices shift if a posting omits a field — defensive parse:
  if fewer than 5 items, map by whatever icons/keywords you can, or
  just take what's there in order and leave the rest None)
.BodyTop_postedSpec__hg2U0                           -> posted_date
.BodyCenter_main__Sz_2E                              -> description
```

`rate` does not exist on this site — leave `None` always.

## Acceptance criteria

- `IamexpatAdapter.site_id == "iamexpat"`, `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` on the fixture yields real stubs; pagination loop terminates cleanly when a page has no cards (test with a mocked second "empty" page).
- `parse_detail()` on the fixture returns `title == "Junior DevOps Engineer IAM (Ping DS/IDM)"`, `client == "Swisscom"`, `location == "Rotterdam"`, `posted_date` containing `"September 24, 2026"`, non-empty `description`, `rate is None`.

## Definition of done

Per Appendix A.
