# E5-S03: Tender-Link site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`,
`E1-S01`. Style reference: `job_scraper/sites/pro_act.py`.

## Goal

A `SiteAdapter` for tender-link.nl (`site_id = "tender_link"`,
`base_url = "https://tender-link.nl"`, `fetch_strategy =
FetchStrategy.STATIC`). Listing and detail both come from a single open
JSON API — no CSS selectors, no separate pagination.

## Context

Create: `job_scraper/sites/tender_link.py`, `tests/test_tender_link.py`.

Fixture (read-only, real API response, trimmed to 3 records for size —
company logos replaced with a placeholder string, everything else real):
- `tests/fixtures/tender_link/listing.json`

`fetch_page` returns raw bytes; `json.loads(page)` accepts bytes directly.

## Listing: `LISTING_URL = "https://tender-link.nl/wp-json/sdcx/v2/vacancies/all"`

Plain GET (fits the standard `fetch_page(self.fetch_strategy,
self.LISTING_URL)` pattern — no POST needed here, unlike stone-interim).
Response shape: `{"status": ..., "total_no_of_records_found": N,
"vacancies": [ ... ]}`. **All records come back in one call — no
pagination** (confirmed: this project's own count of 239 matched the API's
own `total_no_of_records_found`; there is no `page`/`offset` param needed
or supported).

Per-record fields for the `ListingStub`: `vacancyID` (→ `listing_id`,
`str()` it), `slug` (→ `detail_url =
f"https://tender-link.nl/vacature/{slug}/"`), `jobTitle` (→ `title`).

## Detail

A separate detail-page fetch is possible (`/vacature/<slug>/`) but
redundant — the listing record already has every field a detail fetch
would add (confirmed via reconnaissance: the detail page just repeats the
same data in a `<script type="application/ld+json">` block and an inline
`sd_vacancy_data` JS variable). **Don't fetch a separate detail page for
this adapter** — instead, have `list_postings()` stash each record's full
dict somewhere `parse_detail()` can retrieve it by `listing_id` (e.g. an
instance-level `dict[str, dict]` populated as `list_postings()` iterates,
keyed by `vacancyID`), so `parse_detail(stub, page)` can ignore `page`
entirely and just look up the already-parsed record.

Field mapping from a record:
```
jobTitle / titleInformation      -> title
companyName                      -> client
toCategoryNode                   -> category (e.g. "Detachering")
toBrancheLevel2                  -> store in extra_fields["Branche"] (e.g. "Gemeenten")
workLocation or toProvince1Node  -> location
hoursPerWeek                     -> hours (str() it)
contractPeriod                   -> duration
publicationStart                 -> posted_date
vacancyNo                        -> store in extra_fields["vacancyNo"]
```

Rate: this site has two different, non-equivalent salary concepts on the
same record — flag rather than pick blindly:
```
minSalary / maxSalary / toSalaryPeriodNode   -> rate, formatted like
    f"{minSalary}-{maxSalary} {toSalaryPeriodNode}" (e.g. "68-81 per maand")
additionalInfo.vacancy.<id>.value            -> a DIFFERENT gross-salary
    figure for a salaried/payroll variant of the same posting (e.g. "5400"
    rendering elsewhere as "Deta. bruto p/m: €5400") — do NOT use this one
    for `rate`; store it in extra_fields["salaried_gross_monthly"] instead
    if present, since it answers a different question (payroll gross pay,
    not contractor rate).
```

Description: concatenate (as HTML-stripped text) `introInformation`,
`companyInformation`, and whichever of `vacancyInformation` /
`offerInformation` / `requirementsInformation` /
`functionContactInformation` are present and non-empty on the record.

## Acceptance criteria

- `TenderLinkAdapter.site_id == "tender_link"`, `fetch_strategy ==
  FetchStrategy.STATIC`.
- `list_postings()` given the fixture yields exactly 3 stubs (the fixture
  was trimmed to 3 real records), one with `listing_id == "33345"`,
  `detail_url == "https://tender-link.nl/vacature/brp-specialist-33345/"`.
- `parse_detail()` for that stub returns a `JobPosting` with:
  `title == "BRP Specialist"`, `listing_id == "33345"`,
  `site_id == "tender_link"`, `client == "gemeente Soest"`,
  `category == "Detachering"`, `location` containing `"Soest"` or
  `"Utrecht"`, `hours == "40"`, `duration == "6 maanden"`,
  `rate` containing `"68"` and `"81"` (not `"5400"`),
  `extra_fields.get("salaried_gross_monthly") == "5400"`, non-empty
  `description`.
- No live network calls in tests.

## Definition of done

Per Appendix A.
