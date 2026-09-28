# E6-S04: Freelancer.com site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`. Style reference: `job_scraper/sites/pro_act.py`.

## Goal

`site_id = "freelancer_com"`, `base_url = "https://www.freelancer.com"`, `fetch_strategy = FetchStrategy.STATIC`, `LISTING_URL = "https://www.freelancer.com/jobs/software-testing/"`.

## Context

Create: `job_scraper/sites/freelancer_com.py`, `tests/test_freelancer_com.py`.
Fixtures: `tests/fixtures/freelancer_com/listing.html`, `tests/fixtures/freelancer_com/detail_40724221.html`.

## Listing

Card: `div.JobSearchCard-item div.JobSearchCard-item-inner[data-project-card="true"]`. Title + detail URL: `a.JobSearchCard-primary-heading-link` (href is the detail path, e.g. `/projects/mobile-app-testing/astrology-app-tester-required`). **No separate id attribute exists — use the URL path (or its final segment) as `listing_id`.**

**Pagination**: real (`div.Pagination` with `a.Pagination-item[rel="next"]`), but the `software-testing` category currently fits on one page (confirmed: `#total-results-bottom` shows "30 of 30 entries", First/Next/Last all point to the same URL). Implement the loop generically anyway (follow `rel="next"` until it's absent or points to the current page) so it works once this category grows past one page.

## Detail

```
h1                                                   -> title
h2 immediately following the h1                      -> rate (e.g. "₹12500-37500 INR")
"Posted" text + fl-relative-time span                -> posted_date (relative text, e.g. "6 days ago")
plain <p> after a "•" separator                       -> duration (e.g. "Ends in 20 hours")
p.Project-description.whitespace-pre-line             -> description
a[fltrackinglabel="ProjectViewLoggedOut-SkillTag"]     -> category (join all, or take first —
                                                          e.g. "Testing/QA")
```
`listing_id` cross-check: literal text "Project ID: <digits>" inside a `<p>` near the top (class is a shared utility class, not unique — match by regex `r"Project ID:\s*(\d+)"` on the page text, don't rely on a specific selector for this one).

**`client` does not exist anywhere on this site's logged-out view** — verified genuinely absent, not a selector miss. Leave `None` always.

A `<script id="webapp-state" type="application/json">` blob also exists with the same fields in clean structured form — you may use it INSTEAD of the CSS selectors above if you find it more reliable once you inspect the real fixture, but it's not required.

## Acceptance criteria

- `FreelancerComAdapter.site_id == "freelancer_com"`, `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` on the fixture yields real stubs, one with `listing_id` matching (or ending in) `"astrology-app-tester-required"` or `"40724221"` (whichever your id-extraction produces — be consistent, just make sure it's derived from the real URL/page text, not fabricated).
- `parse_detail()` returns `title == "Astrology App QA Tester Required"`, `rate` containing `"12500"`, `client is None`, non-empty `description`.

## Definition of done

Per Appendix A.
