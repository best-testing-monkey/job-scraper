# E3-S01: Pro-Act site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`
(`SiteAdapter`, `FetchStrategy`, `ListingStub`) and `E1-S01` (`JobPosting`).
Does NOT depend on `E2-S04` (pipeline) — this story only builds the adapter
module and its own tests, using saved fixture HTML directly, not through the
pipeline's `fetch_page`.

## Goal

A `SiteAdapter` for pro-act.nl/vacatures (`site_id = "pro_act"`,
`base_url = "https://pro-act.nl"`, `fetch_strategy = FetchStrategy.STATIC`)
that parses real listing and detail HTML into `ListingStub`/`JobPosting`.

## Context

Create: `job_scraper/sites/pro_act.py`, `tests/test_pro_act.py`.

Fixtures already exist (read-only, real saved HTML from live reconnaissance
— do not re-fetch, do not modify):
- `tests/fixtures/pro_act/listing.html`
- `tests/fixtures/pro_act/detail_8887.html` (a posting titled "Agile Coach")

`list_postings()` and `parse_detail()` take pre-fetched pages, not URLs — in
this story's own tests, load the fixture files directly (`Path(...).
read_text()`) and parse them with whatever HTML library you use
(`scrapling`'s own parser, `lxml`, or `BeautifulSoup` — your choice; whatever
you pick becomes a new dependency to add to `pyproject.toml` if not already
there from `E0-S01`'s `scrapling[fetchers]`).

## Selectors and structure (from reconnaissance — verify against the actual
fixture files, which are more authoritative than this description if they
disagree)

**Listing page** (`listing.html`): each posting is an
`article.vacancy-item`. Title + detail URL: `h3 a.link-overlay` (its text,
stripped, is the title; its `href` is already an absolute URL). Hours:
`span.hours` (raw text like `"40 uren per week"`, needs whitespace
collapsing). `listing_id`: not a DOM attribute — parse the trailing digits
from the detail URL's path with a regex like `-(\d+)/?$`.

**Detail page** (`detail_8887.html`, "Agile Coach", `listing_id="8887"`):
- Title: the `h1` inside `#section-vacancy-info .main-info`.
- Dates: `#section-vacancy-info span.date` is ONE element containing both a
  posted and an expiry date separated by `<br>` — its text looks like
  `"Geplaatst: 25 september 2026Verloopt: 30 september 2026"` once tags are
  stripped. Split on `"Verloopt:"` to get `posted_date = "25 september
  2026"` and an expiry string `"30 september 2026"` (store expiry in
  `extra_fields["Verloopt"]`, there's no dedicated `JobPosting` field for
  it).
- Hours: `.vacancy-meta` has repeating `div.name`/`div.answer` pairs; this
  page only has one pair, `name` text `"Uren per week"`, `answer` text
  `"40"` — use the `answer` text as `hours`.
- `client`, `location`, `rate` are NOT separate DOM fields — they're free
  text inside `.section-content .content-wrapper`, under a
  `<strong>Algemene informatie</strong>` heading followed by a `<ul>` of
  `"Label: value"` lines (e.g. `"Tarief: marktconform"`, `"Locatie:
  hybride"`) and a preceding `<p>` mentioning the client (e.g. `"...
  eindklant de Universiteit van Amsterdam (UvA)..."`). Parse the `<ul>` by
  splitting each `<li>`'s text on the first `": "`. For `client`, extract
  with a regex against the preceding paragraph's text, e.g.
  `r"eindklant (?:de |het )?([^.,]+)"` (test it against the real fixture
  text and adjust if it doesn't cleanly capture `"Universiteit van
  Amsterdam (UvA)"` — the fixture is ground truth, not this description).
  These three fields are best-effort: if the regex/heading isn't found,
  leave them `None` rather than raising.
- `description`: the full visible text of `.section-content .content-wrapper`
  (tags stripped, whitespace collapsed) — it's fine that this also includes
  the "Algemene informatie" list text; don't try to exclude it.
- **Gotcha**: the page's `<body>` has a class like `postid-15704` — a
  WordPress-internal ID that is NOT the same as the URL-based listing ID
  (`8887`). Always derive `listing_id` from the URL, never from `postid-*`.

## Acceptance criteria

- `ProActAdapter.site_id == "pro_act"`, `base_url ==
  "https://pro-act.nl"`, `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` given the parsed `listing.html` fixture yields at least
  1 `ListingStub`, and at least one of them has `listing_id == "8887"`
  (cross-check against the detail fixture you also have).
- `parse_detail()` given the `detail_8887.html` fixture (and a stub with
  `listing_id="8887"`) returns a `JobPosting` with:
  `title == "Agile Coach"`, `listing_id == "8887"`, `site_id == "pro_act"`,
  `hours == "40"`, `posted_date == "25 september 2026"`,
  `extra_fields["Verloopt"] == "30 september 2026"`,
  and non-empty `description`.
- `client`, `location`, `rate` are populated with the best-effort
  extraction where possible (`client` containing `"Universiteit van
  Amsterdam"`, `location == "hybride"`, `rate == "marktconform"`, allowing
  minor whitespace/capitalization differences) — if your regex genuinely
  can't extract one of these from the real fixture after reasonable effort,
  it's acceptable for that one field to be `None`, but you must document
  which field and why in your final report.
- `tests/test_pro_act.py` covers all of the above using the real fixture
  files (no live network).

## Definition of done

Per Appendix A.
