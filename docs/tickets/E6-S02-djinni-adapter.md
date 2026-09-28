# E6-S02: Djinni site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`. Style reference: `job_scraper/sites/synprofs.py` (also prefers JSON-LD over CSS).

## Goal

`site_id = "djinni"`, `base_url = "https://djinni.co"`, `fetch_strategy = FetchStrategy.STATIC`, `LISTING_URL = "https://djinni.co/jobs/keyword-QA/"` (a real, verified QA filter — not a guess).

## Context

Create: `job_scraper/sites/djinni.py`, `tests/test_djinni.py`.
Fixtures: `tests/fixtures/djinni/listing.html`, `tests/fixtures/djinni/detail_848723.html`.

## Listing

Card: `div.job-item` — its `id` attribute is `job-item-<listing_id>` (strip the prefix, no URL parsing needed). Detail link: `a.job_item__header-link` inside the card, `href` is the relative detail URL. Title: `h2.job-item__position`.

**Pagination**: real, confirmed — `ul.pagination.pagination_with_numbers` with real `<a class="page-link" href="?page=N">`. Implement generically (follow the "next" link until absent), same pattern as `sevenstars.py`.

## Detail — **prefer JSON-LD** (`script[type="application/ld+json"]`, schema.org JobPosting):

```
title                                  -> title
hiringOrganization.name                -> client
category                               -> category (e.g. "QA")
jobLocation.address.addressCountry     -> location
datePosted                             -> posted_date
validThrough                           -> extra_fields["validThrough"]
employmentType                         -> extra_fields["employmentType"]
identifier                             -> cross-check against stub.listing_id
description                            -> description (full text, already untruncated)
```

`rate` and `duration` do not exist anywhere on this site (verified: only a relative `$$$$` tier badge on listing cards, no numeric salary; no contract-length concept at all) — leave both `None` always.

CSS fallback (only if JSON-LD parsing fails for some reason — not the primary path): `h1.m-0.mb-1.fs-2` (title), `a.text-secondary.fw-medium[href*="/jobs/company-"]` (client), `div.job-post__description` (description).

## Acceptance criteria

- `DjinniAdapter.site_id == "djinni"`, `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` on the fixture yields real stubs including one with `listing_id == "848723"`.
- `parse_detail()` on the fixture returns `title == "Senior Manual QA Engineer - Warsaw (On-site)"`, `client` containing `"Digis"`, `category == "QA"`, `location` containing `"Poland"`, `posted_date` containing `"2026-09-26"`, `rate is None`, `duration is None`, non-empty `description` (~2400 chars, matching JSON-LD).

## Definition of done

Per Appendix A.
