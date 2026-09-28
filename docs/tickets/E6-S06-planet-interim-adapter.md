# E6-S06: Planet Interim site adapter

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E2-S03`, `E1-S01`, STEALTH support. Style reference: `job_scraper/sites/circle8.py` (partial/gated-field pattern).

## Goal

`site_id = "planet_interim"`, `base_url = "https://planetinterim.nl"`, `fetch_strategy = FetchStrategy.STEALTH`, `LISTING_URL = "https://planetinterim.nl/vind-interim-opdrachten"`.

**Known, accepted scope limit**: this site is partially login-gated. `client` and `description` require "Word lid of log in" and are NOT obtainable — every posting from this adapter has `client = None`, `description = ""`, and a `scrape_note` explaining the gate. Everything else (title, location, hours, category, sector, duration, rate when disclosed) is genuinely public. **Pagination is JS-postback-based (`__doPostBack`), not a plain link — out of scope, page 1 only**, same limitation category as `circle8`.

## Context

Create: `job_scraper/sites/planet_interim.py`, `tests/test_planet_interim.py`.
Fixtures: `tests/fixtures/planet_interim/listing.html`, `tests/fixtures/planet_interim/detail_539572.html`.

## Listing

Card: `article.pi-card`. Title + detail URL: `h3 a.stretched-link` (href e.g. `/beleidsadviseur-digitaal-veilig/539572/p13/default.html`). `listing_id`: numeric segment in the URL.

## Detail

```
h1.pi-title                                      -> title
.pi-meta-grid .pi-meta-row (label/value pairs,
  match by .pi-meta-label text, not position):
    "Standplaats"              -> location
    "Duur opdracht"            -> duration
    "Indicatie uurtarief"      -> rate
    "Aantal uren per week"     -> hours
    "Laatste update"           -> posted_date
    "Opdrachtgever"            -> will show a login-gate link instead of a
                                   real value — detect this (e.g. check if
                                   the value cell contains an <a> with
                                   "log in"/"lid" text) and set client=None
.pi-job-group-row .tag-pill span                 -> category
```

Description accordion, `.pi-accordion-item`: the section titled "Profiel van de geschikte interim professional" is public (a candidate-profile bullet list, not the real job description) — don't use it as `description`, it's not equivalent content. The sections with the real content ("Kort bedrijfsprofiel", "Taken & verantwoordelijkheden") are gated the same way as the client field. Set `description = ""` and `scrape_note = "Client name and job description require Planet Interim membership/login — not scraped."`.

## Acceptance criteria

- `PlanetInterimAdapter.site_id == "planet_interim"`, `fetch_strategy == FetchStrategy.STEALTH`.
- `list_postings()` on the fixture yields real stubs, one with `listing_id == "539572"`.
- `parse_detail()` returns `title` containing `"Beleidsadviseur"`, `location == "Zoetermeer"`, `hours == "24"`, `client is None`, `description == ""`, non-empty `scrape_note`.

## Definition of done

Per Appendix A.
