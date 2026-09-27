# E3-S03: FlexValue site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`
(`SiteAdapter`, `FetchStrategy`, `ListingStub`) and `E1-S01` (`JobPosting`).
Does NOT depend on `E2-S04` (pipeline).

## Goal

A `SiteAdapter` for aanvragen.flexvalue.nl/careers/6605 (a CATS ATS portal;
`site_id = "flexvalue"`, `base_url = "https://aanvragen.flexvalue.nl"`,
`fetch_strategy = FetchStrategy.STATIC`) that parses real listing and detail
HTML into `ListingStub`/`JobPosting`.

## Context

Create: `job_scraper/sites/flexvalue.py`, `tests/test_flexvalue.py`.

Fixtures already exist (read-only, real saved HTML from live reconnaissance
— do not re-fetch, do not modify):
- `tests/fixtures/flexvalue/listing.html`
- `tests/fixtures/flexvalue/detail_1065407.html` (a posting titled "Java
  Devops Engineer")

Use whichever HTML-parsing library the other adapter stories are using
(check `pyproject.toml`/`job_scraper/sites/pro_act.py` if present; otherwise
your choice, added to `pyproject.toml`).

## Selectors and structure (from reconnaissance — verify against the actual
fixture files, which are more authoritative than this description if they
disagree)

**Listing page** (`listing.html`): each posting IS an anchor element,
`div.jobs-table div.grid-table a.table-row`. Title:
`div.data-cell.title-cell` inside it. `href` is RELATIVE — join with
`"https://aanvragen.flexvalue.nl"`. `listing_id`: parse the leading digits
from the href with a regex like `/jobs/(\d+)-`.

**Detail page** (`detail_1065407.html`, "Java Devops Engineer",
`listing_id="1065407"`):
- Title: `main#job div.job-header h1`.
- A short location tag: `main#job div.job-header ul.job-tags li` (e.g.
  `"Apeldoorn, Gelderland"`) — use this as `JobPosting.location`.
- `main#job div.job-description` contains an embedded `<table>` of
  key/value rows PLUS free text. Table row selector: `table tr` — within
  each row, `td:nth-child(1) b` is the label, `td:nth-child(2)` is the
  value. Observed labels for this fixture: `Start`, `Einddatum`, `Optie op
  verlenging`, `Uren per week`, `Locatie` (a second, more specific location
  value than the job-tags one — different string, both real), `Deadline`.
  Map: `hours = ` the `"Uren per week"` row's value; `duration =
  f"{start} - {einddatum}"` using the `"Start"`/`"Einddatum"` row values;
  everything else from the table (`"Optie op verlenging"`, `"Deadline"`,
  and the table's own `"Locatie"` value under the key `"Locatie (detail)"`
  to avoid colliding with the job-tags-derived `location` field) goes into
  `extra_fields` keyed by its Dutch label text.
- `client`: NOT a table field — embedded as a `<b>` tag inside a free-text
  sentence elsewhere in `.job-description`, following the word
  "opdrachtgever" (e.g. `"Voor onze opdrachtgever de <b>Belastingdienst</b>
  zijn wij op zoek naar..."`). Find the text "opdrachtgever" (case
  insensitive) in the free-text portion of `.job-description` (i.e. outside
  the `<table>`), then take the nearest following `<b>` tag's text as
  `client`. Best-effort: if not found, leave `None` rather than raising.
- `description`: the free-text portions of `.job-description` OUTSIDE the
  `<table>` (the "Opdrachtbeschrijving"/"Achtergrond opdracht" sections —
  `<b>` headings followed by `<br>`-separated paragraphs), tags stripped
  and whitespace collapsed. It's fine if this ends up including the
  client-mentioning sentence too.
- `category`, `rate`: not present in this fixture; leave `None`.

## Acceptance criteria

- `FlexValueAdapter.site_id == "flexvalue"`,
  `base_url == "https://aanvragen.flexvalue.nl"`,
  `fetch_strategy == FetchStrategy.STATIC`.
- `list_postings()` given the parsed `listing.html` fixture yields at least
  1 `ListingStub` with an absolute `detail_url`, and at least one has
  `listing_id == "1065407"`.
- `parse_detail()` given the `detail_1065407.html` fixture (and a stub with
  `listing_id="1065407"`) returns a `JobPosting` with:
  `title == "Java Devops Engineer"`, `listing_id == "1065407"`,
  `site_id == "flexvalue"`,
  `location == "Apeldoorn, Gelderland"`,
  `hours == "36"`,
  `duration` containing both `"12-10-2026"` and `"31-12-2026"`,
  `extra_fields["Optie op verlenging"] == "Ja"`,
  and non-empty `description`.
- `client` is populated best-effort (`"Belastingdienst"`, allowing minor
  whitespace differences) — if it genuinely can't be extracted after
  reasonable effort, document that in your final report.
- `tests/test_flexvalue.py` covers all of the above using the real fixture
  files (no live network).

## Definition of done

Per Appendix A.
