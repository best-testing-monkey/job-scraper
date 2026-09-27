# Appendix A: implementation standards

Read this once; every story in `docs/tickets/` references it instead of
repeating it.

## Environment & commands

- This project uses `uv`. Always run Python via `uv run <cmd>`, never bare
  `python`/`python3` (not guaranteed on PATH / won't see the project venv).
- Install/sync deps: `uv sync` (reads `pyproject.toml`).
- Run tests: `uv run pytest tests/ -q`.
- Lint: `uv run ruff check .` (if `ruff` isn't yet a dependency when your
  story runs, skip this gate and note it in your report — don't add ruff
  yourself unless your story is specifically about scaffolding).

## Code style

- Python 3.11+, type hints on all function signatures.
- Plain `sqlite3` — no ORM.
- No comments explaining *what* code does (names should do that). A short
  comment is fine only for a genuinely non-obvious constraint (e.g. why a
  regex is shaped a certain way).
- Dataclasses for data models (see `job_scraper/core/models.py`), not dicts
  passed around loosely.
- Keep each story's diff scoped to exactly the files listed in its ticket's
  Context section. Don't refactor or "improve" unrelated code.
- Don't add error handling, retries, or validation for cases the story's
  acceptance criteria don't test. Don't add config options, CLI flags, or
  abstractions beyond what the story asks for.

## Testing conventions

- Tests live under `tests/`, mirroring `job_scraper/`'s structure
  (`tests/test_<module>.py`).
- Adapter/parser tests are fixture-based only — read HTML from
  `tests/fixtures/<site_id>/*.html`, never make live network calls in a test.
- Use plain `assert` statements (pytest style), not `unittest.TestCase`.
- One test file's assertions should be independently runnable:
  `uv run pytest tests/test_<module>.py -q`.

## Git / commit conventions

- One commit per story.
- Commit message: `<Story ID>: <one-line summary>` (e.g. `E1-S01: Add
  JobPosting and ListingStub dataclasses`).
- Stage only the files your story touches — never `git add -A`.
- End every commit message with:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  ```

## Definition of done (applies to every story unless its ticket says otherwise)

1. The exact files listed in the story's Context are created/modified — no
   other files touched.
2. `uv run pytest tests/ -q` passes, including any new tests the story adds.
3. Changes are committed per the commit conventions above.
4. Report back: which files changed, the test command you ran, and its
   output (pass count / failures).
