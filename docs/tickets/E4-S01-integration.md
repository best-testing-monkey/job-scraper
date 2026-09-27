# E4-S01: End-to-end smoke test and README update

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S04`
(pipeline/CLI) and `E3-S05` (all adapters registered).

## Goal

Prove the whole pipeline works together against real fixture data (not live
network — fixtures already exist under `tests/fixtures/<site_id>/` from the
Epic 3 adapter stories), and document usage for a human.

## Context

Create: `tests/test_integration.py`.
Modify: `README.md` (currently just a one-line placeholder: `# job-scraper` /
`An extendable job scraper, for when i'm on the hunt.`).
Read (do not modify): `tests/test_pro_act.py`, `tests/test_hero.py`,
`tests/test_flexvalue.py` (for the fixture-loading pattern each already
uses), and the fixture files under `tests/fixtures/pro_act/`,
`tests/fixtures/hero/`, `tests/fixtures/flexvalue/`.

Read `docs/DESIGN_DOC.md` in full for the CLI usage and cross-repo
integration example — reuse its exact command examples in the README rather
than inventing new ones.

## `tests/test_integration.py`

For each of the 3 registered site ids (pro_act, hero, flexvalue —
freelance.nl was excluded, see `docs/DESIGN_DOC.md`), monkeypatch
`job_scraper.pipeline.fetch_page` so that, instead of a real Scrapling call,
it loads and parses the corresponding saved fixture HTML file from
`tests/fixtures/<site_id>/` (reuse whatever HTML-loading helper each
adapter's own test file already uses — check `tests/test_<site_id>.py` for
the pattern). Run `pipeline.run(["pro_act", "hero", "flexvalue"], repo,
tmp_jobs_dir)` (use the adapters' real `site_id` values) end-to-end and
assert:
- every site's counters show at least 1 `"written"` posting,
- at least one `.md` file exists per site under `tmp_jobs_dir`,
- re-running `pipeline.run` a second time with the same fixtures produces
  `"written": 0` for every site (nothing changed, so nothing is rewritten)
  while `"seen"` counts stay the same.

## README.md

Replace the placeholder with: a one-paragraph description (scrapes NL
interim/zzp job sites into SQLite + markdown, extendable via `SiteAdapter`),
a "Usage" section with the `uv run python -m job_scraper scrape --site
all` / `list-sites` commands, a "Currently supported sites" list (the 3
site ids), and an "Integration with resume-matcher" section showing the
`--jobs "../scraper/jobs/*.md"` example from the design doc.

## Acceptance criteria

- `uv run pytest tests/ -q` passes, including the new integration test.
- `README.md` documents real, currently-working commands (not aspirational
  ones for Epic 2/3 sites that don't exist yet).

## Definition of done

Per Appendix A.
