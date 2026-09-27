# job_scraper implementation todo

Ordered by dependency graph. Stories in the same epic with no dependency on
each other (noted inline) can run as parallel subagents since they touch
disjoint files.

## Epic 0 — Scaffolding

- [ ] E0-S01 Project scaffolding (pyproject.toml, package skeleton) (docs/tickets/E0-S01-project-scaffolding.md)

## Epic 1 — Core data model & storage

- [ ] E1-S01 JobPosting and ListingStub dataclasses (docs/tickets/E1-S01-models.md)
- [ ] E1-S02 SQLite schema and JobRepository (docs/tickets/E1-S02-db.md) — parallel-safe with E1-S03
- [ ] E1-S03 Markdown exporter (docs/tickets/E1-S03-markdown-export.md) — parallel-safe with E1-S02

## Epic 2 — Shared pipeline infrastructure

- [ ] E2-S01 robots.txt pre-check (docs/tickets/E2-S01-robots-check.md) — parallel-safe with E1-S02/E1-S03 (only depends on E0-S01)
- [ ] E2-S02 Exclusion keyword filter and dedup helper (docs/tickets/E2-S02-filters.md)
- [ ] E2-S03 SiteAdapter base class, FetchStrategy enum, empty registry (docs/tickets/E2-S03-adapter-base.md) — parallel-safe with E2-S01/E2-S02
- [ ] E2-S04 Pipeline orchestration and CLI entrypoint (docs/tickets/E2-S04-cli-pipeline.md)

## Epic 3 — Site adapters (Pro-Act, Hero, FlexValue — freelance.nl excluded, see DESIGN_DOC.md)

- [ ] E3-S01 Pro-Act adapter (docs/tickets/E3-S01-pro-act-adapter.md) — parallel-safe with E3-S02/E3-S03
- [ ] E3-S02 Hero adapter (docs/tickets/E3-S02-hero-adapter.md) — parallel-safe with E3-S01/E3-S03
- [ ] E3-S03 FlexValue adapter (docs/tickets/E3-S03-flexvalue-adapter.md) — parallel-safe with E3-S01/E3-S02
- [ ] E3-S05 Wire all three adapters into the registry (docs/tickets/E3-S05-wire-registry.md)

## Epic 4 — Integration

- [ ] E4-S01 End-to-end smoke test and README update (docs/tickets/E4-S01-integration.md)
