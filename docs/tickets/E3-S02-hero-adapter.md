# E3-S02: Hero site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`
(`SiteAdapter`, `FetchStrategy`, `ListingStub`) and `E1-S01` (`JobPosting`).
Does NOT depend on `E2-S04` (pipeline).

## Goal

A `SiteAdapter` for hero.eu/interim-opdrachten (`site_id = "hero"`,
`base_url = "https://hero.eu"`, `fetch_strategy = FetchStrategy.STATIC`)
that parses real listing and detail HTML into `ListingStub`/`JobPosting`.

## Context

Create: `job_scraper/sites/hero.py`, `tests/test_hero.py`.

Fixtures already exist (read-only, real saved HTML from live reconnaissance
— do not re-fetch, do not modify):
- `tests/fixtures/hero/listing.html`
- `tests/fixtures/hero/detail_e98187b8.html` (a posting titled "Cloud Engineer")

Use the same HTML-parsing library choice as your `pyproject.toml` already
has from `E0-S01`/`E3-S01` (check `pyproject.toml` and `job_scraper/sites/
pro_act.py` if it exists yet, for consistency — but if it doesn't exist yet
because stories run in parallel, choosing `scrapling`'s built-in parser or
`lxml`/`BeautifulSoup` is fine, just add whichever you pick to
`pyproject.toml`'s dependencies if not already present).

## Selectors and structure (from reconnaissance — verify against the actual
fixture files, which are more authoritative than this description if they
disagree)

**Listing page** (`listing.html`, server-rendered): each posting is an
`li.py-3` inside `ul.divide-y.border-y`. Title + detail URL: `h5.hero-h5 a`
(text = title; `href` is RELATIVE — join with `"https://hero.eu"`).
Per-item metadata: `div.hero-caption span.whitespace-nowrap` — exactly 5
spans per item, in this fixed order: `[0]` posted date, `[1]` category,
`[2]` location, `[3]` hours/week, `[4]` work mode. Each span also contains a
nested `<span aria-hidden>·</span>` separator (absent on the last one) —
take the span's own leading text, stripped of any trailing `·` and
whitespace. `listing_id`: parse the trailing 8 lowercase-hex-character
segment from the detail URL with a regex like `-([0-9a-f]{8})$`.

**Detail page** (`detail_e98187b8.html`, "Cloud Engineer",
`listing_id="e98187b8"`):
- Title: `h1.hero-h2` — contains a trailing decorative `<span>` (a caret
  icon); strip it, keep just the text.
- Metadata: `ul.mt-4.gap-x-6 li.hero-lead` — for this posting there are 3
  such `li`s. Within each, take the SECOND `<span>` (the first is a
  decorative `aria-hidden` bullet). Its text is a `"Label: Value"` string —
  split on `": "` to get the field name and value. (In the raw fixture file
  this may render oddly across HTML comment nodes; parse it as one
  concatenated string via your HTML library's `.text` / `get_text()`
  accessor, not by reading raw bytes.)
- Description: `div.hero-requisition-body p` — take the first (only)
  paragraph's text as `description`. It's a visually-blurred teaser in the
  original page's CSS, but the raw HTML text is complete and unobscured.
- `category` and `posted_date` are NOT present anywhere on the detail page
  — they only exist on the listing page. Since this adapter's
  `parse_detail(stub, page)` only receives the detail page, leave
  `category`/`posted_date` as `None` in this story (a future story could
  thread listing-page metadata through into `parse_detail` via `stub`, but
  that's out of scope here — don't add it).
- `client`, `rate`, `duration`: not present on the detail page at all;
  leave `None`.

## Acceptance criteria

- `HeroAdapter.site_id == "hero"`, `base_url == "https://hero.eu"`,
  `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` given the parsed `listing.html` fixture yields at least
  1 `ListingStub` with an absolute (not relative) `detail_url`, and at
  least one has `listing_id == "e98187b8"`.
- `parse_detail()` given the `detail_e98187b8.html` fixture (and a stub
  with `listing_id="e98187b8"`) returns a `JobPosting` with:
  `title == "Cloud Engineer"`, `listing_id == "e98187b8"`,
  `site_id == "hero"`,
  `location == "Maasland"`,
  `hours == "36 uur/week"` (or equivalent — match whatever the raw label
  text actually is; assert on the "Value" part after the label split),
  and `description` containing the substring `"Cloud Engineer voor het
  programma Grensverleggende IT"`.
- `tests/test_hero.py` covers all of the above using the real fixture
  files (no live network).

## Definition of done

Per Appendix A.
