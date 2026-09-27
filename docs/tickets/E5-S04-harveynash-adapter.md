# E5-S04: Harvey Nash site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`,
`E1-S01`. Style reference: `job_scraper/sites/pro_act.py`.

## Goal

A `SiteAdapter` for harveynash.nl (`site_id = "harveynash"`,
`base_url = "https://www.harveynash.nl"`, `fetch_strategy =
FetchStrategy.STATIC`). Listing source is the site's XML sitemap (the
`/vacatures` page itself is confirmed broken/empty — don't use it). Detail
pages are real, clean Next.js pages with a `__NEXT_DATA__` JSON blob.

## Context

Create: `job_scraper/sites/harveynash.py`, `tests/test_harveynash.py`.

Fixtures (read-only, real data):
- `tests/fixtures/harveynash/sitemap.xml` — real sitemap, 139 total URLs
- `tests/fixtures/harveynash/detail_299204.html` — real detail page
  ("Expert (gas)regelvermogen Weert" / Enexis)
- `tests/fixtures/harveynash/listing.html` — the confirmed-broken
  `/vacatures` page (kept as a negative-case reference; don't use it for
  extraction, it's not needed by `list_postings()`)

## Listing: `LISTING_URL = "https://www.harveynash.nl/sitemap.xml"`

Plain XML, `<url><loc>...</loc></url>` per entry. **Filter carefully**:
not every `/vacatures/` URL is a real job — the sitemap also contains
non-job utility pages like `/vacatures/internal` and
`/vacatures/thank-you-for-applying`. Only match URLs of the form
`https://www.harveynash.nl/vacatures/<digits>-<slug>` — use a regex like
`r"/vacatures/(\d+)-"` and skip any `<loc>` that doesn't match. This
yields ~31 real job URLs (confirmed count at reconnaissance time; will
drift as postings change). No pagination in the sitemap itself (single
flat file).

`listing_id` = the digits captured by that regex. Title isn't in the
sitemap — use a placeholder (e.g. derived from the slug) since
`parse_detail` sets the real title from `__NEXT_DATA__`.

## Detail

Extract the JSON from `<script id="__NEXT_DATA__"
type="application/json">...</script>` (BeautifulSoup:
`soup.find("script", id="__NEXT_DATA__")`), `json.loads()` its text, then
navigate to `data["props"]["pageProps"]["page"]`. Fields:

```
page["title"]         -> title
page["location"]      -> location  (e.g. "Weert, Limburg")
page["published_at"]  -> posted_date
page["expires_at"]    -> store in extra_fields["expires_at"]
page["description"]   -> description (HTML — strip tags)
```

`categories` is a list of `{"name": ..., "values": [{"name": ...}, ...]}`
groups — look up by `name`:
```
"Clients"            -> client (first value's name)
"Functie categorie"   -> category (join all values' names with ", " if
                         more than one)
"Employment type"     -> store in extra_fields["employment_type"]
"Aantal uren"         -> hours
```

Rate: `page["salary_package"]` is a free-text field (e.g. `"Bespreekbaar"`
= "negotiable") — use it as `rate` directly when non-empty.
`salary_low`/`salary_high` are numeric but were both `"0.0"` on the sample
fixture (negotiable postings don't populate them) — if both are non-zero
on a future posting, prefer formatting `f"{salary_low}-{salary_high}"` as
`rate` instead of `salary_package`; for THIS fixture, `salary_package`
("Bespreekbaar") is what the test should assert.

## Acceptance criteria

- `HarveyNashAdapter.site_id == "harveynash"`, `fetch_strategy ==
  FetchStrategy.STATIC`.
- `list_postings()` given the sitemap fixture yields real job stubs only
  (excludes `/vacatures/internal`, `/vacatures/thank-you-for-applying`,
  `/vacatures/thank-you-for-submitting-cv`, and any other non-numeric-ID
  URL), with at least one `listing_id == "299204"`.
- `parse_detail()` given the detail fixture returns a `JobPosting` with:
  `title == "Expert (gas)regelvermogen Weert"`, `listing_id == "299204"`,
  `site_id == "harveynash"`, `client == "Enexis"`,
  `category` containing `"Techniek"` or `"Projectbeheersing"`,
  `location == "Weert, Limburg"`, `hours == "Fulltime"`,
  `rate == "Bespreekbaar"`, `extra_fields.get("employment_type") ==
  "Interim"`, non-empty `description`.
- No live network calls in tests.

## Definition of done

Per Appendix A.
