# E6-S10: freelancermap.de site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`, STEALTH support. Style reference: `job_scraper/sites/circle8.py` for class shape; this site's extraction is closer to `headfirst.py`'s JSON-in-page pattern than a simple CSS-selector adapter.

## Goal

`site_id = "freelancermap"`, `base_url = "https://www.freelancermap.de"`, `fetch_strategy = FetchStrategy.STEALTH`, `LISTING_URL = "https://www.freelancermap.de/projekte?query=Playwright"` (a real, verified test-automation-relevant filter).

**Known, accepted scope limit**: pagination has a real UI component, but the `?pagenr=N` URL param does NOT actually paginate (confirmed: still returns page-1 content) — real pagination is click/XHR-only. Page 1 only (~22 results), documented via `scrape_note`.

## Context

Create: `job_scraper/sites/freelancermap.py`, `tests/test_freelancermap.py`.
Fixtures: `tests/fixtures/freelancermap/listing.html`, `tests/fixtures/freelancermap/detail_test-automation-consultant-m-w-d-playwright.html`.

## Listing — prefer the embedded JSON over DOM scraping

The listing page embeds a React-on-Rails hydration payload:
`<script type="application/json" class="js-react-on-rails-component" data-component-name="ProjectSearch">{...}</script>`.
Parse its `initialResults` array — each element is one project with real fields: `id` (numeric), `slug`, `title`, `description` (HTML), `company` (top-level — real client name when disclosed, otherwise absent/null), `poster` (agency/account info), `country`, `locations`, `created` (ISO timestamp). Use `id` as `listing_id`, build `detail_url` as `f"{base_url}/projekt/{slug}"`.

DOM fallback (only if the JSON script tag isn't found — inspect the real fixture first, it should be there): card = `div.project-card`; title+URL = `a[data-testid="title"]` (href `/projekt/<slug>`); skip cards where `span[data-testid="top-project"]` is present (sponsored slots, not organic results, would skew a "listing count" expectation — note this in your report if you keep or drop them, either is acceptable, just be consistent).

## Detail

```
h1.h2.mg-b-display-m                                        -> title
badge with i.fa-location-pin                                -> location
badge with i.fa-file-contract                                -> extra_fields["contract_type"]
  (e.g. "Freiberuflich" = freelance)
badge with i.far.fa-calendar                                 -> extra_fields["start_date"]
  (e.g. "ab sofort")
badge with i.fa-hourglass                                    -> duration (e.g. "Dauer 3 Monate")
badge with i.fa-briefcase                                    -> hours (e.g. "100% Auslastung")
text "veröffentlicht am DD.MM.YYYY"                          -> posted_date
a[data-id="project-body-keyword-link"]                       -> category (join all skill tags)
div.project-body-description .ql-editor                      -> description
```

`.project-info-name` (labelled "Ansprechpartner") is a CONTACT PERSON, not a company — do not map it to `client`. **`client` is frequently absent on this site** (only a contact person's name, no company) — when the listing JSON's `company` field is null/missing for this posting, leave `client = None` rather than substituting the contact person's name. `rate`/budget does not exist on this specific posting (verified — freelancermap allows undisclosed rates); leave `None` if genuinely absent from both the JSON and the detail page, don't force a value.

## Acceptance criteria

- `FreelancermapAdapter.site_id == "freelancermap"`, `fetch_strategy == FetchStrategy.STEALTH`.
- `list_postings()` on the fixture yields real stubs (~22, page 1 only).
- `parse_detail()` for the "Test Automation Consultant (m/w/d) Playwright" posting returns `title` containing `"Test Automation Consultant"`, `duration` containing `"3 Monate"`, `hours` containing `"100%"`, category containing `"Playwright"`, non-empty `description`, non-empty `scrape_note` mentioning the pagination limitation. `client` may legitimately be `None` for this posting — don't force a value if the source doesn't have one.

## Definition of done

Per Appendix A.
