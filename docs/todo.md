# job_scraper implementation todo

Ordered by dependency graph. Stories in the same epic with no dependency on
each other (noted inline) can run as parallel subagents since they touch
disjoint files.

## Epic 0 — Scaffolding

- [x] E0-S01 Project scaffolding (pyproject.toml, package skeleton) (docs/tickets/E0-S01-project-scaffolding.md)

## Epic 1 — Core data model & storage

- [x] E1-S01 JobPosting and ListingStub dataclasses (docs/tickets/E1-S01-models.md)
- [x] E1-S02 SQLite schema and JobRepository (docs/tickets/E1-S02-db.md) — parallel-safe with E1-S03
- [x] E1-S03 Markdown exporter (docs/tickets/E1-S03-markdown-export.md) — parallel-safe with E1-S02

## Epic 2 — Shared pipeline infrastructure

- [x] E2-S01 robots.txt pre-check (docs/tickets/E2-S01-robots-check.md) — parallel-safe with E1-S02/E1-S03 (only depends on E0-S01)
- [x] E2-S02 Exclusion keyword filter and dedup helper (docs/tickets/E2-S02-filters.md)
- [x] E2-S03 SiteAdapter base class, FetchStrategy enum, empty registry (docs/tickets/E2-S03-adapter-base.md) — parallel-safe with E2-S01/E2-S02
- [x] E2-S04 Pipeline orchestration and CLI entrypoint (docs/tickets/E2-S04-cli-pipeline.md)

## Epic 3 — Site adapters (Pro-Act, Hero, FlexValue — freelance.nl excluded, see DESIGN_DOC.md)

- [x] E3-S01 Pro-Act adapter (docs/tickets/E3-S01-pro-act-adapter.md) — parallel-safe with E3-S02/E3-S03
- [x] E3-S02 Hero adapter (docs/tickets/E3-S02-hero-adapter.md) — parallel-safe with E3-S01/E3-S03
- [x] E3-S03 FlexValue adapter (docs/tickets/E3-S03-flexvalue-adapter.md) — parallel-safe with E3-S01/E3-S02
- [x] E3-S05 Wire all three adapters into the registry (docs/tickets/E3-S05-wire-registry.md)

## Epic 4 — Integration

- [x] E4-S01 End-to-end smoke test and README update (docs/tickets/E4-S01-integration.md)

## Epic 5 — Second-wave site adapters (synprofs, stone-interim, tender-link, harveynash, headfirst, sevenstars, circle8)

Recon found every one of these needs a different approach than assumed in
`scrape-targets.md`: 4 have hidden JSON APIs or sitemaps substituting for
broken/client-rendered listing pages, 1 (headfirst) needs JSON-in-script
parsing with documented partial coverage, and 2 (sevenstars, circle8) need
`FetchStrategy.STEALTH` (a real anti-detect browser) since they're behind
a Vercel WAF, not actually robots.txt-blocked as first thought.
overheidsopdrachten.nl was dropped — confirmed still a broken Blazor app
with no usable API. Pagination was checked per-site during recon; none of
these need pagination-following except headfirst (browser-only, out of
scope, documented as a known gap).

- [x] E5-S01 Synprofs adapter (docs/tickets/E5-S01-synprofs-adapter.md) — parallel-safe with E5-S02..S07
- [x] E5-S02 Stone Interim adapter (docs/tickets/E5-S02-stone-interim-adapter.md) — parallel-safe with E5-S01, E5-S03..S07
- [x] E5-S03 Tender-Link adapter (docs/tickets/E5-S03-tender-link-adapter.md) — parallel-safe with E5-S01/S02, E5-S04..S07
- [x] E5-S04 Harvey Nash adapter (docs/tickets/E5-S04-harveynash-adapter.md) — parallel-safe with E5-S01..S03, E5-S05..S07
- [x] E5-S05 HeadFirst adapter (docs/tickets/E5-S05-headfirst-adapter.md) — parallel-safe with E5-S01..S04, E5-S06/S07 (assign to Sonnet: RSC chunk parsing is more complex than the others)
- [x] E5-S06 Sevenstars adapter (docs/tickets/E5-S06-sevenstars-adapter.md) — parallel-safe with E5-S01..S05, E5-S07
- [x] E5-S07 Circle8 adapter (docs/tickets/E5-S07-circle8-adapter.md) — parallel-safe with E5-S01..S06
- [x] E5-S08 Wire second-wave adapters into registry (docs/tickets/E5-S08-wire-registry-v2.md)
- [x] E5-S09 Extend integration test and README for second-wave sites (docs/tickets/E5-S09-integration-update.md)

**Live verification (2026-09-28)**: full `scrape --site all` run against all 10
real sites — 369 postings written (circle8 9, flexvalue 14, harveynash 29,
headfirst 10, hero 49, pro_act 9, sevenstars 15, stone_interim 24, synprofs
27, tender_link 183), 1 cross-site duplicate correctly caught (not double
exported), idempotent on rerun. Also fixed a real bug found only by this
live run (not by any unit test): `robots_allowed()` failed closed instead
of open when a WAF fronted a robots.txt fetch with 403 — see the
`core/robots.py` commit.

## Post-implementation bugfix (found via live-site verification, not a separate story)

`list_postings()` had no consistent way to fetch a real listing page (3
adapters each guessed a different broken pattern: a required `page` arg
that the real pipeline never passes, an `Any = None` default that silently
no-ops, and a `self.page` attribute nobody ever sets) — a gap in how the
adapter stories were specified, not a Haiku implementation error. Fixed by
moving `fetch_page` into `sites/base.py` (accessible to both `pipeline.py`
and every adapter without a circular import) and giving each adapter a
`LISTING_URL` that its own `list_postings()` fetches via `fetch_page`.
Also fixed: `fetch_page` was returning Scrapling's raw `Response` object
instead of `.html_content`, which would have broken `parse_detail` on real
(non-fixture) pages too. Also fixed: Pro-Act's description extraction swept
in an unrelated application-form field ("In loondienst" as a submission-type
checkbox option), causing every single Pro-Act posting to trip the
exclusion-keyword filter as a false positive.
Verified via a real live scrape of all 3 sites: 73 postings written
(flexvalue 14/14, hero 50/50, pro_act 9/10 — 1 legitimately excluded).
