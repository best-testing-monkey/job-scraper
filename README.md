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

## Currently supported sites

- `pro_act` — Pro-Act IT (pro-act.nl/vacatures)
- `hero` — Hero Interim (hero.eu/interim-opdrachten)
- `flexvalue` — FlexValue (aanvragen.flexvalue.nl/careers)

None of the three currently paginate their listing page — each adapter
fetches exactly one listing URL. A future site with genuine multi-page
listings would need pagination handling added to its own adapter.

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
