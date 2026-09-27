# E1-S03: Markdown exporter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E1-S01`
(`job_scraper/core/models.py` must already define `JobPosting`).

## Goal

Render a `JobPosting` into the exact markdown format `resume-matcher`'s
`jobs/*.md` files already use, and write it to disk with a stable,
collision-free filename.

## Context

Create: `job_scraper/core/markdown_export.py`, `tests/test_markdown_export.py`.

Reference format (from
`../resume-matcher/jobs/freelapp-508877-tester-rvo.md`, read-only reference,
do not modify that file):

```
# Tester (RVO, remote in Nederland)

- Source: https://freelapp.nl/freelance-opdracht/tester/508877
- Client: Rijksdienst voor Ondernemend Nederland (RVO)
- Category: Test Engineer (IT &amp; technologie)
- Level: Senior
- Posted: 2026-08-07 08:08:59
- Location: Nederland, remote (per description: "remote in Nederland")
- Hours: 36 uur/week
- Rate: not stated

## Description

Voor de Rijksdienst voor Ondernemend Nederland...
```

## Functions to implement

```python
def slugify(text: str) -> str:
    """Lowercase, non-alphanumeric runs -> single hyphen, no leading/
    trailing hyphens. e.g. "Senior Tester (RVO)!" -> "senior-tester-rvo"."""

def filename_for(posting: JobPosting) -> str:
    """f"{posting.site_id}-{posting.listing_id}-{slugify(posting.title)}.md" """

def render(posting: JobPosting) -> str:
    """Returns the full markdown text: '# {title}' header, then one
    '- {Field}: {value}' bullet per populated field in this order: Source
    (= source_url), Client, Category, Level, Status, Location, Hours, Rate,
    Duration, Posted (= posted_date), Experience, Skills (comma-joined if
    non-empty). Skip any field that is None/empty (don't render a bullet
    for it at all). Then render one '- {Key}: {value}' bullet per entry in
    extra_fields (in insertion order), then a blank line, '## Description',
    a blank line, description text. If scrape_note is set, append a blank
    line, '## Scrape note', a blank line, scrape_note text."""

def write(posting: JobPosting, jobs_dir: str) -> str:
    """Ensures jobs_dir exists, writes render(posting) to
    jobs_dir/filename_for(posting), returns the full path written."""
```

## Acceptance criteria

- `slugify("Spoed | Test Automation Engineer | Overheid")` produces a
  hyphenated, lowercase, alphanumeric-only slug with no double hyphens
  (e.g. `spoed-test-automation-engineer-overheid` or equivalent — exact
  wording doesn't matter, but the shape rules above must hold).
- `filename_for` matches the existing naming convention exactly for a
  constructed `JobPosting(site_id="freelapp", listing_id="508877", title="Tester (RVO, remote in Nederland)", ...)`
  → the result must look like `freelapp-508877-tester-rvo-remote-in-nederland.md`
  (some slug of the title is fine; site_id-listing_id-prefix must match
  exactly).
- `render()` on a `JobPosting` with every field populated produces text
  containing a `# {title}` header, a bullet for every populated field in
  the order given above, `## Description` followed by the description
  text, and `## Scrape note` followed by scrape_note text.
- `render()` on a minimal `JobPosting` (only required fields set, everything
  else default) produces NO bullets for the unset optional fields and NO
  `## Scrape note` section, but still has `## Description` (even if
  description is empty string, the header is still present).
- `write()` creates the directory if missing and the file's content exactly
  equals `render(posting)`.
- `tests/test_markdown_export.py` covers all of the above with concrete
  `assert` statements comparing exact strings/substrings, using `tmp_path`
  for `write()`'s directory.

## Definition of done

Per Appendix A.
