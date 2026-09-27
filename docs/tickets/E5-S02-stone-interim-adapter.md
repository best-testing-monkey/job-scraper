# E5-S02: Stone Interim site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`,
`E1-S01`. Style reference: `job_scraper/sites/pro_act.py`.

## Goal

A `SiteAdapter` for stone-interim.nl (`site_id = "stone_interim"`,
`base_url = "https://www.stone-interim.nl"`, `fetch_strategy =
FetchStrategy.STATIC`). This site's human-facing pages are an empty React
shell — real data comes entirely from two internal JSON API endpoints. No
HTML parsing at all in this adapter.

## Context

Create: `job_scraper/sites/stone_interim.py`, `tests/test_stone_interim.py`.

Fixtures (read-only, real API responses from reconnaissance):
- `tests/fixtures/stone_interim/listing_api_GetOverviewItems.json` — real
  response, 24 items (top-level: `Items` list, `TotalCount`)
- `tests/fixtures/stone_interim/detail_4893_api_GetVacancy.json` — real
  response for "Interim Supply Chain Manager" (id 4893)

`fetch_page` returns raw bytes; `json.loads(page)` accepts bytes directly.

## Listing

The listing endpoint is a **POST**, not a GET — `fetch_page` (GET-only)
doesn't cover this, so `list_postings()` must make its own direct call:

```python
from scrapling.fetchers import Fetcher
import json

response = Fetcher.post(
    "https://www.stone-interim.nl/api/v1/WordPress/GetOverviewItems/",
    json={
        "pageKind": "job-overview", "file_name": "job-overview", "lang": "",
        "taxonomies_to_filter": [], "searchQuery": "",
        "start_index": 0, "page_size": 50,
    },
)
data = json.loads(response.body)
```

(In tests, monkeypatch this differently than the other adapters — see
Acceptance criteria below; don't try to route this through the shared
`fetch_page` mock pattern, since it's a POST with a body, not a GET.)

Each item in `data["Items"]`: `Title`, `LinkUrl` (relative, e.g.
`/opdrachten/id/4893/Interim+Supply+Chain+Manager/Interim/` — the numeric
segment after `/id/` is the listing id). Build `ListingStub.detail_url` as
the **detail API URL** (not the human page), since that's what the shared
pipeline will `fetch_page(STATIC, stub.detail_url)` for the detail step:
`f"https://www.stone-interim.nl/api/v1/WordPress/GetVacancy/{listing_id}"`.
`page_size: 50` already covers all 24 current postings in one call — no
pagination loop needed (confirmed via reconnaissance: `TotalCount` matches
a 24-entry sitemap cross-check).

## Detail (`parse_detail(stub, page)` — `page` is the raw bytes of a GET to
the URL above; `json.loads(page)` it)

```
data["TitleInformation"]  -> title
data["PublicationStart"]  -> posted_date
data["PublicationEnd"]    -> store in extra_fields["PublicationEnd"]
cr = data["ToVacancy"]["CRVacancy"]
cr.get("CompanyName")                          -> client (verified: None
                                                   on the id-4893 fixture —
                                                   this site anonymizes some
                                                   postings; leave None when
                                                   absent, don't treat as a bug)
cr["HoursPerWeek"]                             -> hours (str() it)
cr["ToProvince1Node"]["CRDataNode"]["Value"]   -> location
cr["ToFunctionLevel1"]["CRDataNode"]["Value"]  -> category
cr["ToContractTypeNode"]["CRDataNode"]["Value"] or
cr["ToProductNode"]["CRDataNode"]["Value"]     -> duration (whichever is
                                                   populated; if both, join)
```

Description: concatenate whichever of these are non-empty (they're HTML
strings): `cr["IntroInformation"]`, `cr["VacancyInformation"]`,
`cr["OfferInformation"]`, `cr["Requirements"]`, `cr["CompanyInformation"]`.
Strip HTML tags for the final `description` string (reuse a simple
tag-strip regex, or BeautifulSoup's `get_text()` — your choice).

`rate` is genuinely absent from this site's data (verified across multiple
postings during reconnaissance, not a scraping gap) — leave `None` always
for this adapter, don't attempt to find it.

## Acceptance criteria

- `StoneInterimAdapter.site_id == "stone_interim"`, `fetch_strategy ==
  FetchStrategy.STATIC`.
- `tests/test_stone_interim.py`: for `list_postings()`, monkeypatch
  `scrapling.fetchers.Fetcher.post` (via `unittest.mock.patch`) to return an
  object whose `.body` is the real fixture file's bytes, then confirm at
  least 24 stubs yielded, one with `listing_id == "4893"`.
- `parse_detail()` given the detail fixture's raw bytes (read the fixture
  file with `Path(...).read_bytes()`, not `.read_text()`, to match what
  `fetch_page` really returns) returns a `JobPosting` with:
  `title == "Interim Supply Chain Manager"`, `listing_id == "4893"`,
  `site_id == "stone_interim"`, `client is None` (verified: this posting's
  `CompanyName` is null — anonymized), `hours == "40"`,
  `location == "Noord Brabant"`, `category == "Technology"`,
  `rate is None`, non-empty `description`.
- No live network calls in tests.

## Definition of done

Per Appendix A.
