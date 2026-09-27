# E2-S02: Exclusion keyword filter and duplicate detection helper

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E1-S01`
(`JobPosting`) and `E1-S02` (`JobRepository`, for the dedup helper's type
signature — it takes a repository instance).

## Goal

Two independent pieces of filtering logic used by the pipeline: dropping
postings that explicitly rule out zzp/freelance work, and flagging
duplicate postings that appear under multiple bureaus.

## Context

Create: `job_scraper/core/filters.py`, `tests/test_filters.py`.

Import `JobPosting` from `job_scraper.core.models`, `JobRepository` from
`job_scraper.core.db` (both already exist from Epic 1).

## Functions to implement

```python
EXCLUSION_KEYWORDS = (
    "geen zzp",
    "zzp niet toegestaan",
    "enkel detachering",
    "in loondienst",
)

def is_excluded(posting: JobPosting) -> bool:
    """Case-insensitive substring match of any EXCLUSION_KEYWORDS entry
    against posting.description. Returns True if the posting should be
    dropped (not stored, not exported)."""

def apply_dedup(posting: JobPosting, repo: JobRepository) -> JobPosting:
    """Normalizes posting.title/client/location (lowercase, strip, collapse
    whitespace) and calls repo.find_duplicate(...) with the normalized
    values. If a match is found, returns a copy of posting with a new
    field/attribute set indicating the duplicate target (see note below);
    if no match, returns posting unchanged."""
```

Note on `apply_dedup`'s return value: `JobPosting` (from E1-S01) does not
currently have a `duplicate_of` field — that's a `JobRepository`/SQL-layer
concept, not a domain concept, per the design doc. Rather than adding a
field to `JobPosting` in this story, have `apply_dedup` return a tuple
`(posting: JobPosting, duplicate_of_id: int | None)` instead of just a
`JobPosting`. Update this ticket's acceptance criteria assumption
accordingly: `apply_dedup` returns `tuple[JobPosting, int | None]`.

## Acceptance criteria

- `is_excluded` returns `True` for a posting whose description contains
  `"Let op: geen ZZP'ers"` (case-insensitive match on `"geen zzp"`), and for
  each of the other three keywords in isolation.
- `is_excluded` returns `False` for a posting whose description contains
  none of the keywords.
- `apply_dedup`, given a `JobRepository` (real instance, temp SQLite file)
  with one existing row `title="Senior Tester"`, `client="Acme BV"`,
  `location="Den Haag"`, and a new posting with
  `title="  SENIOR   tester "`, `client="acme bv"`, `location="den haag"`
  (different case/whitespace, same normalized identity), returns that
  existing row's id as the second tuple element.
- `apply_dedup`, given a posting with no matching existing row, returns
  `(posting, None)`.
- `tests/test_filters.py` covers all of the above with real `JobRepository`
  instances (temp SQLite file via `tmp_path`) for the dedup tests — no
  mocking of `JobRepository` itself.

## Definition of done

Per Appendix A.
