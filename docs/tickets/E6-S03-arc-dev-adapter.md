# E6-S03: Arc.dev site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`. Style reference: `job_scraper/sites/pro_act.py`.

## Goal

`site_id = "arc_dev"`, `base_url = "https://arc.dev"`, `fetch_strategy = FetchStrategy.STATIC`, `LISTING_URL = "https://arc.dev/remote-jobs/qa-engineer"`.

**Known, accepted scope limit**: this listing currently has exactly **one** real job card (verified directly — an earlier fast triage's "~32 postings" count was a false positive from counting category-chip/nav links, not job cards). Don't try to find more; one is correct for this fixture and likely typical for this niche filter. **No pagination exists in static HTML** (confirmed: no next-page link/param anywhere) — implement `list_postings()` without a pagination loop for this adapter.

## Context

Create: `job_scraper/sites/arc_dev.py`, `tests/test_arc_dev.py`.
Fixtures: `tests/fixtures/arc_dev/listing.html`, `tests/fixtures/arc_dev/detail_pg2lgfgv87.html`.

## Listing

Card: `div.job-card` (has real `data-testid="job-card"` and `data-job-random-key` attributes — prefer these over positional/hashed classes). Detail link/title: `a.job-title`, href e.g. `/remote-jobs/j/ladders-senior-software-engineer-test-core-pg2lgfgv87`. `listing_id` = the card's `data-job-random-key` attribute (or the trailing slug segment, same value).

## Detail (no JSON-LD JobPosting on this site — only a BreadcrumbList, already checked and ruled out; use CSS)

```
h1.title                                          -> title
a.company-name                                    -> client
```

The rest is a label/value list, `div.details > div`, each with `h3 span.title` (label) + `div.value` (value) — match by label text, not position:
```
"Location"          -> location (may be vague, e.g. "Remote restrictions apply" — use as-is)
"Salary Estimate"    -> rate (literal "N/A" seen — a real value, not missing data; keep as the string if present, or None if the row is absent)
"Seniority"          -> extra_fields["seniority"]
"Tech stacks" (or similar) -> category
"Visa"                -> extra_fields["visa"] if present
```
The last row has no `h3` label — `div.value.single-line` with two child `div`s: first child is contract type (e.g. "Permanent role") -> `duration`, second child is a relative posted date (e.g. "a month ago") -> `posted_date`.

Description: `div.tab#tab-job-details`.

## Acceptance criteria

- `ArcDevAdapter.site_id == "arc_dev"`, `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` on the fixture yields exactly 1 stub, `listing_id == "pg2lgfgv87"`.
- `parse_detail()` returns `title == "Senior Software Engineer, Test Core"`, `client == "Ladders"`, `rate == "N/A"`, `duration` containing `"Permanent"`, non-empty `description`.

## Definition of done

Per Appendix A.
