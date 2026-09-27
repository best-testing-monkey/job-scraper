# E0-S01: Project scaffolding

Read `docs/tickets/APPENDIX-A-standards.md` first.

## Goal

Set up the `uv`-managed package skeleton so every later story has somewhere
to put code and a working `uv run pytest` gate.

## Context

Repo root: `/media/baz/MonkeyWorks/PycharmProjects/job-hunter/scraper/`
(already contains `README.md`, `scrape-targets.md`, `.gitignore`, `LICENSE`,
`docs/DESIGN_DOC.md`, `docs/tickets/`). Nothing under `job_scraper/` or
`tests/` exists yet — you are creating it all.

Read `docs/DESIGN_DOC.md`'s "Package layout" and "Dependencies" sections for
the target structure.

## Files to create

- `pyproject.toml` — project name `job-scraper`, Python `>=3.11`,
  dependencies: `scrapling[fetchers]`, dev dependency: `pytest`.
- `job_scraper/__init__.py` (empty)
- `job_scraper/core/__init__.py` (empty)
- `job_scraper/sites/__init__.py` (empty)
- `tests/__init__.py` (empty)
- `tests/fixtures/.gitkeep` (empty file, so the directory exists in git even
  before any fixtures are added)
- `tests/test_scaffolding.py` — a single trivial test:
  `def test_import(): import job_scraper` (proves the package installs and
  imports cleanly)

## Files to modify

- `.gitignore` — append two lines: `jobs/` and `scraper.db` (these are
  generated output directories/files for this project, not present yet, but
  will be once the pipeline runs).

## Acceptance criteria

- `uv sync` completes without error.
- `uv run pytest tests/ -q` passes (1 test, `test_import`).
- `job_scraper`, `job_scraper.core`, `job_scraper.sites` are all importable
  as packages (`uv run python -c "import job_scraper.core, job_scraper.sites"`
  exits 0).
- `.gitignore` contains `jobs/` and `scraper.db` as new entries (don't
  duplicate if something similar already exists — check first).

## Definition of done

Per Appendix A, plus: this is the FIRST story — there is no existing
`pyproject.toml`/lockfile to conflict with, so `uv sync` here also creates
`uv.lock`, which should be committed alongside the other new files.
