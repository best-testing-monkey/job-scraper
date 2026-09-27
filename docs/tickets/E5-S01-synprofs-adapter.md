# E5-S01: Synprofs site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`
(`SiteAdapter`, `FetchStrategy`, `ListingStub`, `fetch_page`) and `E1-S01`
(`JobPosting`). Style reference: `job_scraper/sites/pro_act.py` (an
existing adapter using the same base classes).

## Goal

A `SiteAdapter` for synprofs.nl (`site_id = "synprofs"`,
`base_url = "https://www.synprofs.nl"`, `fetch_strategy =
FetchStrategy.STATIC`). Unlike the first 3 adapters, the listing source is
an XML sitemap, not the site's own listing page (which is a client-side-
rendered dead end — don't use it).

## Context

Create: `job_scraper/sites/synprofs.py`, `tests/test_synprofs.py`.

Fixtures (read-only, real data from reconnaissance):
- `tests/fixtures/synprofs/listing.xml` — real `vacancy-sitemap.xml`, 32 entries
- `tests/fixtures/synprofs/detail_6930.html` — real detail page ("Senior Tester")

`fetch_page` (from `job_scraper.sites.base`) now returns raw `bytes` (not a
string) — both `xml.etree.ElementTree.fromstring()` and
`BeautifulSoup(page, "html.parser")`/`"lxml-xml"` accept bytes directly, no
decoding needed.

## Listing: `LISTING_URL = "https://www.synprofs.nl/vacancy-sitemap.xml"`

Plain XML sitemap, `<url><loc>...</loc></url>` per entry, no pagination (32
entries, single file). URL pattern:
`https://www.synprofs.nl/opdracht/<slug>-<id>/` — parse `id` as the
trailing digits before the final slash, e.g. `.../opdracht/senior-tester-6930/`
→ `listing_id="6930"`. The sitemap has no title — use a placeholder title
in the `ListingStub` (e.g. the slug with hyphens replaced by spaces,
title-cased) since `parse_detail` will set the real title from the detail
page's JSON-LD anyway.

## Detail page (`detail_6930.html`, "Senior Tester", client "Dienst ICT
Uitvoering" / DICTU)

Primary source: the `<script type="application/ld+json">` block — a
schema.org `JobPosting` object. Parse it with `json.loads` after extracting
the script tag's text (BeautifulSoup: `soup.find("script",
type="application/ld+json")`). Fields: `title`, `hiringOrganization.name`
(→ `client`), `jobLocation.address.addressLocality` (→ `location`),
`datePosted` (→ `posted_date`), `validThrough` (→ store in
`extra_fields["validThrough"]`), `identifier.value` (cross-check against
`stub.listing_id`).

Additional fields from `ul.publication-text-vacancy-specs > li` (5 items:
hours, location, start date, duration, deadline) — use whichever aren't
already covered by the JSON-LD block; map hours-like text to `hours`,
duration-like text to `duration`.

Description: concatenate the text of these elements in order (each is an
`h2.sd-block-title-htag` heading + `div.sd-block-text` body, wrapped in a
container — grab both class-named containers' full text):
`.publication-text-introInformation`, `.publication-text-companyInformation`,
`.publication-text-vacancyInformation`, `.publication-text-requirementsInformation`,
`.publication-text-offerInformation`.

`category` and `rate` are NOT cleanly selectable on this site (category is
buried in an inline JS variable requiring a lookup table; rate only
appears as free text like "All-in uurtarief ... €95,00/105,00" inside the
description). Leave both `None` — do not attempt regex extraction for
these two on this site (known, accepted gap, unlike the best-effort regex
approach used for Pro-Act/FlexValue's client field).

## Acceptance criteria

- `SynprofsAdapter.site_id == "synprofs"`, `fetch_strategy ==
  FetchStrategy.STATIC`.
- `list_postings()` given the parsed sitemap fixture yields exactly 32
  stubs, at least one with `listing_id == "6930"`.
- `parse_detail()` given the detail fixture returns a `JobPosting` with
  `title == "Senior Tester"`, `listing_id == "6930"`, `site_id ==
  "synprofs"`, `client` containing `"Dienst ICT Uitvoering"` or `"DICTU"`,
  `location` containing `"Assen"`, `posted_date` containing `"2026-09-25"`
  (or equivalent from the JSON-LD `datePosted`), non-empty `description`,
  `category is None`, `rate is None`.
- `tests/test_synprofs.py` covers all of the above using the real fixtures
  (no live network).

## Definition of done

Per Appendix A.
