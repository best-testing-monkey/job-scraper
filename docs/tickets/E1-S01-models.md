# E1-S01: JobPosting and ListingStub dataclasses

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E0-S01` being
done (needs `job_scraper/core/__init__.py` to exist).

## Goal

Define the two core data classes every other module builds on: `ListingStub`
(what a site's listing page reveals before opening a detail page) and
`JobPosting` (the fully parsed posting).

## Context

Create: `job_scraper/core/models.py`, `tests/test_models.py`.

Read `docs/DESIGN_DOC.md`'s "Data model (`core/models.py`)" section — it
contains the exact dataclass definitions to use, reproduced here for
convenience:

```python
@dataclass
class ListingStub:
    listing_id: str
    detail_url: str
    title: str

@dataclass
class JobPosting:
    site_id: str
    listing_id: str
    source_url: str
    title: str
    client: str | None = None
    category: str | None = None
    level: str | None = None
    status: str | None = None
    location: str | None = None
    hours: str | None = None
    rate: str | None = None
    duration: str | None = None
    posted_date: str | None = None
    experience: str | None = None
    skills: list[str] = field(default_factory=list)
    description: str = ""
    scrape_note: str | None = None
    extra_fields: dict[str, str] = field(default_factory=dict)
```

## Acceptance criteria

- `job_scraper/core/models.py` defines exactly `ListingStub` and
  `JobPosting` as shown above (field names, types, and defaults must match
  exactly — other stories construct these by field name).
- Add a method `JobPosting.content_hash() -> str`: returns a stable
  `hashlib.sha256` hex digest computed over all fields EXCEPT
  `site_id`/`listing_id`/`source_url` (i.e. over the content that would
  change the rendered markdown, not the identity of the row). Two
  `JobPosting`s with identical content but different `source_url` must
  produce the same hash; changing `description` must change the hash.
- `tests/test_models.py` covers: constructing a `JobPosting` with only
  required fields (defaults apply correctly), constructing one with all
  fields populated, and `content_hash()` being stable across two identical
  postings and different when `description` differs.

## Definition of done

Per Appendix A.
