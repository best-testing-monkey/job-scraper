# E1-S02: SQLite schema and JobRepository

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E1-S01`
(`job_scraper/core/models.py` must already define `JobPosting`).

## Goal

Store `JobPosting` rows in SQLite with upsert-by-identity, change detection
via content hash, staleness tracking, and dedup linking.

## Context

Create: `job_scraper/core/db.py`, `tests/test_db.py`.

Read `docs/DESIGN_DOC.md`'s "Storage (`core/db.py`)" section for the exact
schema (reproduced below) and behavior of `upsert`/
`mark_stale_not_seen_since`.

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    site_id TEXT NOT NULL,
    listing_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title TEXT NOT NULL,
    client TEXT, category TEXT, level TEXT, status TEXT,
    location TEXT, hours TEXT, rate TEXT, duration TEXT,
    posted_date TEXT, experience TEXT, skills TEXT,
    description TEXT, scrape_note TEXT,
    extra_fields TEXT,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_stale INTEGER NOT NULL DEFAULT 0,
    duplicate_of INTEGER REFERENCES jobs(id),
    UNIQUE(site_id, listing_id)
);
```

`skills` is stored as a JSON array string (`json.dumps(posting.skills)`).
`extra_fields` is stored as a JSON object string.

Import `JobPosting` from `job_scraper.core.models` (created in E1-S01).

## Class to implement: `JobRepository`

```python
class JobRepository:
    def __init__(self, db_path: str): ...

    def upsert(self, posting: JobPosting, seen_at: str) -> bool:
        """Insert or update the row for (posting.site_id, posting.listing_id).
        `seen_at` is an ISO-8601 timestamp string, always sets last_seen_at
        and is_stale=0; sets first_seen_at only on insert. Returns True if
        this was a new row OR content_hash changed vs. the stored row
        (i.e. the caller should re-export markdown); False if nothing
        about the content changed (only last_seen_at/is_stale moved)."""

    def mark_stale_not_seen_since(self, site_id: str, run_started_at: str) -> int:
        """Set is_stale=1 for every row of this site_id whose last_seen_at
        is earlier than run_started_at. Returns the number of rows updated."""

    def find_duplicate(self, title: str, client: str | None, location: str | None) -> int | None:
        """Case-insensitive, whitespace-normalized match against existing
        rows' (title, client, location). Returns the matching row's id, or
        None if no match. Rows that are themselves duplicates
        (duplicate_of IS NOT NULL) are not matched against."""

    def set_duplicate_of(self, site_id: str, listing_id: str, original_id: int) -> None:
        """Set duplicate_of on the row identified by (site_id, listing_id)."""
```

Create the table (`CREATE TABLE IF NOT EXISTS ...`) in `__init__`, matching
the pattern in `../resume-matcher/job_matcher.py`'s `EmbeddingCache` class
(same repo family, same stdlib `sqlite3` style — you can read that file for
reference if useful, but do not import anything from `resume-matcher`; this
is a separate repo).

## Acceptance criteria

- `tests/test_db.py` uses a temp SQLite file (e.g. `tmp_path` pytest
  fixture) and covers:
  - `upsert` on a brand-new `JobPosting` returns `True` and the row is
    readable back with correct field values (query it directly with
    `sqlite3` in the test, or add a small private helper — don't add a
    public `get_by_key` method unless you need it for the test).
  - Calling `upsert` again with the identical posting (same content) returns
    `False`, and `last_seen_at` in the row has updated to the new
    `seen_at` value while `first_seen_at` is unchanged.
  - Calling `upsert` with the same `(site_id, listing_id)` but a changed
    `description` returns `True`.
  - `mark_stale_not_seen_since` correctly flips `is_stale` to `1` only for
    rows with an earlier `last_seen_at`, leaving rows seen at/after that
    timestamp with `is_stale=0`.
  - `find_duplicate` finds a match on exact (case/whitespace-insensitive)
    title+client+location, returns `None` when there's no match, and never
    matches a row that already has `duplicate_of` set.

## Definition of done

Per Appendix A.
