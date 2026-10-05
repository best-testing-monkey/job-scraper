# job-scraper

An extendable scraper for Dutch interim and ZZP job sites. Scrapes listings into SQLite for deduplication and queryability, then exports postings as Markdown files compatible with `resume-matcher` for scoring and analysis. Built around `SiteAdapter`, a simple interface that decouples site-specific parsing from the shared pipeline, storage, and export layers.

## Usage

List all registered sites:

```bash
uv run python -m job_scraper list-sites
```

Scrape all supported sites and export to markdown:

```bash
uv run python -m job_scraper scrape --site all
```

Scrape a single site:

```bash
uv run python -m job_scraper scrape --site pro_act
```

Rebuild markdown from raw pages:

```bash
uv run python -m job_scraper rebuild --site all
```

Note: `working_nomads`, `tender_link` and `stone_interim` cannot be rebuilt (re-scrape instead, as they cache data during `list_postings`).

Backfill screenshots for existing jobs:

```bash
uv run python -m job_scraper screenshots --site all
uv run python -m job_scraper screenshots --site pro_act --missing-only
```

Screenshots are taken at scrape time by default; this command back-fills existing jobs (`--missing-only` skips ones that already have a PNG).

Repair or backfill stale markers from the database:

```bash
uv run python -m job_scraper stale-sync
```

**Stale postings.** The markdown bullet `- Stale since: YYYY-MM-DD` is written by `scrape` when a posting disappears and removed when it returns. `stale-sync` repairs/backfills it from `scraper.db`; stale rows without a date are dated with the day the command runs. The app hides a stale posting 3 days after that date.

## Currently supported sites

- `pro_act` — Pro-Act IT (pro-act.nl/vacatures)
- `hero` — Hero Interim (hero.eu/interim-opdrachten)
- `flexvalue` — FlexValue (aanvragen.flexvalue.nl/careers); job URLs point at the public careers-portal ad page; the apply form lives under `/apply`
- `synprofs` — Synprofs (synprofs.nl, via its vacancy sitemap)
- `stone_interim` — Stone Interim (stone-interim.nl, via its JSON API)
- `tender_link` — Tender-Link (tender-link.nl, via its JSON API)
- `harveynash` — Harvey Nash (harveynash.nl, via its sitemap)
- `headfirst` — HeadFirst (headfirst.nl) — see its own ticket for scope
  limits: only a partial set of postings, no full description
- `sevenstars` — Sevenstars (sevenstars.nl/opdrachten, paginated)
- `circle8` — Circle8 (circle8.nl/opdrachten)
- `iamexpat` — IamExpat (iamexpat.nl/career/jobs-netherlands, paginated)
- `djinni` — Djinni (djinni.co/jobs, QA keyword filter, paginated)
- `arc_dev` — Arc.dev (arc.dev/remote-jobs/qa-engineer) — no pagination
  exists in static HTML (confirmed: no next-page link/param anywhere); this
  filter typically has exactly one real posting
- `freelancer_com` — Freelancer.com (freelancer.com/jobs/software-testing,
  paginated)
- `guru` — Guru (guru.com/d/jobs) — STEALTH required: guru.com is currently
  blocked site-wide by Incapsula bot-protection for plain HTTP (verified:
  HTTP 403 on every path, including robots.txt)
- `planet_interim` — Planet Interim (planetinterim.nl/vind-interim-opdrachten)
  — client name and job description require Planet Interim
  membership/login; not scraped
- `ictergezocht` — ICTergezocht (ictergezocht.nl/ict-vacatures) —
  pagination is non-functional (all pages return page-1 content); page 1
  only
- `wearedevelopers` — WeAreDevelopers (wearedevelopers.com/jobs, QA filter)
  — page 1 only; pagination is a Hotwire/Turbo "Load more" mechanism not
  yet supported
- `working_nomads` — Working Nomads (workingnomads.com, via its JSON API)
- `freelancermap` — freelancermap (freelancermap.de/projekte, Playwright
  keyword filter) — page 1 only; the `?pagenr=N` query param does not
  paginate on freelancermap (confirmed dead param, real pagination is
  click/XHR-only); ~22 results total for this search

Of these, `sevenstars`, `iamexpat`, `djinni`, `freelancer_com`, and `guru`
paginate their listing pages by following next-page links; every other
adapter either fetches exactly one listing URL or (for `working_nomads`)
gets the full list back from a single API call. A future site with genuine
multi-page listings would need pagination handling added to its own
adapter.

## Screenshots (browser requirements)

Playwright 1.63 expects Chromium revision 1243, whose executable is `/home/baz/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`, and that file exists.

Patchright 1.63 resolves the same executable, `/home/baz/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`, and that file exists.

Scrapling's `StealthyFetcher` launches patchright Chromium (not Camoufox) via `patchright.sync_api`, so it shares the `~/.cache/ms-playwright` install; the screenshot feature needs a second browser download: no.

If a browser is missing, run `uv run playwright install chromium` (warning: `~/.cache/*` physically lands on the crowded `/media/baz/MonkeyWorks` drive and the download is hundreds of MB).

## robots.txt

Every scrape checks `robots.txt` before touching a site, and skips it if
disallowed. Pass `--ignore-robots` to bypass this — only for sites you have
explicit permission to scrape; it does not by itself add support for a new
site (an adapter still has to exist for it).

## Integration with resume-matcher

Point the sibling `resume-matcher` project at the exported job files:

```bash
cd ../resume-matcher
python job_matcher.py --resumes "resumes/*.md" --jobs "../scraper/jobs/*.md" --mode embed
```

All exported markdown follows the format expected by `resume-matcher`, so no additional preprocessing is needed.
