# E6-S08: WeAreDevelopers site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`, STEALTH support. Style reference: `job_scraper/sites/circle8.py`.

## Goal

`site_id = "wearedevelopers"`, `base_url = "https://www.wearedevelopers.com"`, `fetch_strategy = FetchStrategy.STEALTH`, `LISTING_URL = "https://www.wearedevelopers.com/jobs?country=all&q=QA"` (a real, verified QA filter — the site has no category dropdown, only this free-text search box). Note: `jobs.wearedevelopers.com` (a different subdomain sometimes referenced) has no DNS record at all — don't use it.

**Known, accepted scope limit**: pagination is a real Hotwire/Turbo "Load more jobs" mechanism tied to an opaque date+id cursor (`turbo-frame#jobs_pagination`), not a simple page number — out of scope, page 1 only (~24 postings), documented via `scrape_note`.

## Context

Create: `job_scraper/sites/wearedevelopers.py`, `tests/test_wearedevelopers.py`.
Fixtures: `tests/fixtures/wearedevelopers/listing.html`, `tests/fixtures/wearedevelopers/detail_2904764.html`.

## Listing

Card: `article` (no stable class — Tailwind utility soup; matching on the tag plus the presence of `a[href^="/jobs/ext/"]` inside it is the reliable signal). Detail link/id: `a[href^="/jobs/ext/"]` — href format `/jobs/ext/<numeric-id>-<slug>`; `listing_id` = the numeric prefix. Title: `h3` inside that link. Company: first `div.truncate` with no other class in the card. Location: `div.truncate.text-base-content\/60` (note the escaped slash in the class name — CSS attribute/class selectors need this escaped, e.g. via `select_one('div[class*="truncate"][class*="text-base-content/60"]')` if a literal class selector gives you trouble).

## Detail — **prefer `<meta>` tags**, far more stable than the Tailwind DOM:

```
meta[name="job:location"]           -> location
meta[name="job:employment_type"]    -> extra_fields["employment_type"]
meta[name="job:posted_time"]        -> posted_date (already ISO format)
meta[name="job:skill"]  (repeated)  -> category (join all into one string)
meta[property="og:article:author"]  -> client
h1                                   -> title
```

Description: find the `<h2>` whose text is exactly `"Job description"`, then take the very next `div.prose-base-content.prose` sibling's text (there are 3 such prose blocks per page — Job description / Requirements / About the company — matching by the preceding h2's text is required, the class alone isn't unique).

`rate`/`hours`/`duration` do not exist on this site (a permanent-role board, not freelance) — leave all three `None` always. A "Salary insights" nav link is an unrelated false-positive if you grep for "salary" — ignore it.

## Acceptance criteria

- `WearedevelopersAdapter.site_id == "wearedevelopers"`, `fetch_strategy == FetchStrategy.STEALTH`.
- `list_postings()` on the fixture yields real stubs (page 1 only, ~24), one with `listing_id == "2904764"`.
- `parse_detail()` returns `title` containing `"Qa Testing Engineer"` (case as found in the fixture), `client == "AILY LABS"`, `location == "Barcelona, Spain"`, `posted_date == "2026-09-14"`, `rate is None`, non-empty `description`, non-empty `scrape_note` mentioning the pagination limitation.

## Definition of done

Per Appendix A.
