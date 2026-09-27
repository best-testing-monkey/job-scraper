# job_scraper design doc

## Problem

`scrape-targets.md` catalogs ~15+ candidate job sites for interim/zzp test
automation work in the NL market, with per-site access notes already
established by manual research: some are plain static HTML (easy), some
render listings client-side and need a real browser, two disallow automated
access via `robots.txt` (excluded permanently), and some are login-gated
(excluded until further notice). None of this is wired up to code yet.

The sibling project `resume-matcher` (`../resume-matcher/`) already scores
resume-to-job fit, but only against a handful of hand-written example job
files. It reads job postings as plain markdown text files matched by a glob
pattern (`--jobs "<pattern>"`) — no schema, no parsing, the whole file is
passed straight into an LLM prompt. Confirmed by reading
`resume-matcher/jobs/*.md`: every existing file follows the same shape —

```
# <Title>

- Source: <url>
- Listing ID: <id>
- Category: <...>
- ... (other metadata bullets, freely varying per posting)

## Description

<prose>

## Scrape note

<optional prose about what was/wasn't available>
```

This project's job is to produce that data automatically: scrape the
easy/static sites first, store results in SQLite (queryable, dedupeable,
tracks which listings are still live), and export markdown files in the
format above so `resume-matcher` can consume them with zero changes on its
side — just point `--jobs` at this project's output directory.

## Goals

- **Extendable**: adding a new site should mean writing one new adapter
  module and registering it — never touching shared pipeline/storage code.
- **Resilient to per-site heterogeneity**: static HTML, JS-rendered, and
  bot-protected sites all need different fetch strategies; the architecture
  must accommodate all three without forcing every adapter through the
  heaviest one.
- **Idempotent**: re-running a scrape should not create duplicate rows,
  should only rewrite a markdown file when its content actually changed, and
  should be able to tell "still live" apart from "no longer listed."
- **Testable without the network**: parser logic must be verifiable against
  saved HTML fixtures, not live sites (which change and go down).
- **Compatible, not coupled**: output must slot into `resume-matcher` via its
  existing `--jobs` glob flag. No shared code between the two repos.

## Non-goals (this phase)

- Browser-rendered sites (Tender-Land-Link, HeadFirst, Harvey Nash,
  overheidsopdrachten.nl, etc.) — deferred to a later epic once the static
  pipeline is proven.
- `sevenstars.nl` and `circle8.nl` — `robots.txt` disallows automated access;
  not implemented, period.
- Login-gated sources (mijn.freelance.nl full listings, Striive, esd.next) —
  only public, logged-out pages are in scope.
- Cross-repo code sharing with `resume-matcher` — integration is file-glob
  only.

## Architecture

### Fetch strategy per site

[Scrapling](https://github.com/D4Vinci/Scrapling) provides three fetcher
tiers that map directly onto the access notes already in `scrape-targets.md`:

| Strategy | Scrapling class | When |
|---|---|---|
| `STATIC` | `Fetcher` (plain HTTP + TLS impersonation) | Public static HTML — this phase's only sites |
| `STEALTH` | `StealthyFetcher` (anti-bot browser) | Sites with bot/Cloudflare protection — later epic |
| `DYNAMIC` | `DynamicFetcher` (full Playwright/Chromium) | Client-rendered listings (JS builds the DOM) — later epic |

Scrapling also has built-in `robots_txt_obey`, rate limiting (`AutoThrottle`),
retry logic, and CSS/XPath/adaptive selectors — this project uses those
rather than re-implementing them, except for a small standalone
`urllib.robotparser`-based pre-check (`core/robots.py`) so the pipeline can
skip a whole site cleanly (with a log line) before attempting any fetch,
independent of which Scrapling fetcher tier that site ends up using.

### Package layout

```
scraper/
  pyproject.toml
  job_scraper/
    cli.py
    pipeline.py
    core/
      models.py          # JobPosting, ListingStub
      db.py              # sqlite3 schema + JobRepository
      markdown_export.py # JobPosting -> resume-matcher-compatible .md
      filters.py         # exclusion keywords + cross-site dedup
      robots.py          # per-domain robots.txt pre-check
    sites/
      base.py            # SiteAdapter ABC + FetchStrategy enum
      registry.py         # SITE_REGISTRY: dict[str, type[SiteAdapter]]
      pro_act.py
      hero.py
      flexvalue.py
      freelance_nl.py
  tests/
    fixtures/<site>/*.html
    test_<site>.py
    test_markdown_export.py
    test_db.py
    test_filters.py
  jobs/          # generated, gitignored
  scraper.db     # generated, gitignored
```

### Data model (`core/models.py`)

```python
@dataclass
class ListingStub:
    """What's visible from a site's listing page, before opening the detail page."""
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

`extra_fields` is the extensibility escape hatch: a site with a quirky field
that doesn't deserve a first-class column yet (e.g. Pro-Act's "Views"/
"Responses" counters) still gets captured and rendered — nothing is silently
dropped just because a field isn't in the common schema.

### Storage (`core/db.py`)

Plain `sqlite3`, no ORM — matches `resume-matcher`'s existing `EmbeddingCache`
style in `job_matcher.py`.

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
    extra_fields TEXT,            -- JSON blob
    content_hash TEXT NOT NULL,   -- sha256 of the fields that affect the .md output
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_stale INTEGER NOT NULL DEFAULT 0,
    duplicate_of INTEGER REFERENCES jobs(id),
    UNIQUE(site_id, listing_id)
);
```

`JobRepository.upsert(posting) -> bool` returns whether the content actually
changed (new row or `content_hash` differs) — the pipeline only re-writes the
markdown file when this is true, so re-runs are cheap and don't touch git
history / mtimes for unchanged postings.

`JobRepository.mark_stale_not_seen_since(site_id, run_started_at)` flips
`is_stale=1` for any row of that site not touched in the current run — a
listing that's disappeared from the site rather than one that errored out
mid-scrape.

### Dedup (`core/filters.py`)

Per `scrape-targets.md`'s own cross-site finding ("the same requests are
posted on several bureaus... a scraper needs dedupe on title plus client plus
location"): normalize `(title, client, location)` and check against existing
rows before insert. On a match, set `duplicate_of` to the original row's id
rather than dropping the new one — provenance (which bureaus carry this
request) stays queryable, but only the canonical row gets exported to
markdown.

### Exclusion filtering (`core/filters.py`)

Per `scrape-targets.md` section 4, drop (don't store) any posting whose text
contains: `"geen zzp"`, `"zzp niet toegestaan"`, `"enkel detachering"`,
`"in loondienst"` (case-insensitive). This runs after parsing, before dedup
and storage.

### Site adapter contract (`sites/base.py`)

```python
class FetchStrategy(Enum):
    STATIC = "static"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"

class SiteAdapter(ABC):
    site_id: ClassVar[str]
    base_url: ClassVar[str]
    fetch_strategy: ClassVar[FetchStrategy] = FetchStrategy.STATIC

    @abstractmethod
    def list_postings(self) -> Iterator[ListingStub]:
        """Crawl the site's listing page(s), yield one stub per posting."""

    @abstractmethod
    def parse_detail(self, stub: ListingStub, page) -> JobPosting:
        """Given the fetched detail page for a stub, build a JobPosting."""
```

`page` is whatever Scrapling's fetch call for that adapter's `fetch_strategy`
returns (a parseable response object with `.css()`/`.xpath()` etc.) — the
pipeline is responsible for calling the right Scrapling fetcher based on
`fetch_strategy` and handing the adapter only the parsed page, so adapters
never deal with fetch mechanics directly, only HTML → `JobPosting` mapping.

`sites/registry.py` is a plain explicit dict — no auto-discovery magic:

```python
from . import pro_act, hero, flexvalue, freelance_nl

SITE_REGISTRY: dict[str, type[SiteAdapter]] = {
    pro_act.ProActAdapter.site_id: pro_act.ProActAdapter,
    hero.HeroAdapter.site_id: hero.HeroAdapter,
    flexvalue.FlexValueAdapter.site_id: flexvalue.FlexValueAdapter,
    freelance_nl.FreelanceNlAdapter.site_id: freelance_nl.FreelanceNlAdapter,
}
```

### This phase's three adapters (all `FetchStrategy.STATIC`)

Per `scrape-targets.md` section 1, confirmed by live reconnaissance
(fixtures saved under `tests/fixtures/<site_id>/`):

- **Pro-Act** (`pro-act.nl/vacatures`) — 14 assignments, title + hours/week
  on the listing page; detail pages at `/vacatures/<slug>-<id>/`.
- **Hero** (`hero.eu/interim-opdrachten`) — 36 assignments; listing page has
  date/category/location/hours/work-mode; detail at
  `/interim-opdrachten/<slug>-<8hex>`.
- **FlexValue** (`aanvragen.flexvalue.nl/careers/6605`, a CATS ATS portal) —
  15 assignments with deadlines; detail at `/careers/6605/jobs/<id>-<slug>`.

**freelance.nl is excluded from this phase**, contrary to the original plan.
Reconnaissance found two independent blockers: (1) its `robots.txt`
explicitly disallows `/` for `User-agent: *`, whitelisting only specific
named bots (Googlebot, Bingbot, GPTBot, ClaudeBot, etc.) — not a generic
scraper's identity, so this project's own `robots_allowed()` check correctly
excludes it, same as `sevenstars.nl`/`circle8.nl`; (2) its listing/category
pages (`/opdrachten`, `/opdrachten/testen`) are a client-rendered Gatsby SPA
with zero job links in the raw HTML — not static, contrary to
`scrape-targets.md`'s assumption. Two useful findings preserved for a future,
explicitly-permissioned epic: its detail pages ARE static/clean and, in the
two samples checked, were NOT actually login-gated (full description text
was public) — and postings can be discovered without a browser via its
sitemap (`sitemaps/sitemap-projects.xml.gz`, served as plain XML, ~5205
entries). Not pursued further now; revisit only if explicit permission from
the site is obtained.

### Markdown export (`core/markdown_export.py`)

Filename: `{site_id}-{listing_id}-{slug(title)}.md` — matches the existing
examples exactly (`freelance-nl-1183973-test-automation-engineer.md`,
`freelapp-508877-tester-rvo.md`). Renders: `# {title}`, then one `- {Field}:
{value}` bullet per populated `JobPosting` field (skip `None`/empty, render
`extra_fields` the same way), then `## Description` with the prose, then
`## Scrape note` if `scrape_note` is set.

### Pipeline (`pipeline.py`)

```
for site in selected_sites:
    if not robots_allowed(site.base_url):
        log_skip(site); continue
    run_started_at = now()
    for stub in site.list_postings():
        page = fetch(site.fetch_strategy, stub.detail_url)
        posting = site.parse_detail(stub, page)
        if is_excluded(posting):
            continue
        posting = apply_dedup(posting, repo)
        changed = repo.upsert(posting, seen_at=run_started_at)
        if changed and posting.duplicate_of is None:
            markdown_export.write(posting, jobs_dir)
    repo.mark_stale_not_seen_since(site.site_id, run_started_at)
```

### CLI (`cli.py`)

```
python -m job_scraper scrape --site <site-id>|all [--dry-run]
python -m job_scraper list-sites
python -m job_scraper export --site <site-id>|all   # re-render markdown from DB without re-scraping
```

### Testing strategy

All adapter/parser tests run against saved HTML fixtures
(`tests/fixtures/<site>/*.html`) — never live network. This makes acceptance
criteria mechanical and checkable without flakiness: "given this fixture,
`parse_detail` returns a `JobPosting` with `title == "..."`, `client ==
"..."`, etc." `core/db.py`, `core/markdown_export.py`, and `core/filters.py`
each get direct unit tests independent of any adapter.

### Dependencies

`scrapling[fetchers]` (this phase only needs the plain `Fetcher`; `scrapling
install` for browser binaries is deferred to the later browser-based epic),
stdlib `sqlite3` / `urllib.robotparser` / `hashlib`, `pytest`. Managed via
`uv` + `pyproject.toml`.

## Integration with resume-matcher

No code coupling. `resume-matcher/job_matcher.py` already accepts arbitrary
glob patterns for `--jobs`; pointing it at this project's output is a
one-flag change:

```bash
cd ../resume-matcher
python job_matcher.py --resumes "resumes/*.md" --jobs "../scraper/jobs/*.md" --mode embed
```

## Future epics (not this phase)

- **Epic 2 — browser-based sites**: Tender-Link, HeadFirst, Harvey Nash,
  overheidsopdrachten.nl, etc., using `FetchStrategy.STEALTH`/`DYNAMIC`
  adapters. Same `SiteAdapter` contract, no changes to core pipeline/storage.
- **Epic 3 — scheduling**: recurring scrape runs (cron/schedule skill),
  reusing the idempotent upsert + staleness tracking already built in.
