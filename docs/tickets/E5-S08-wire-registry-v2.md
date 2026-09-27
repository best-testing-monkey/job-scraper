# E5-S08: Wire second-wave adapters into the registry

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E5-S01`
through `E5-S07` (all second-wave adapter modules must already exist) and
the existing `job_scraper/sites/registry.py` (currently has `pro_act`,
`hero`, `flexvalue` registered from the first wave).

## Goal

Register the second-wave adapters (synprofs, stone_interim, tender_link,
harveynash, headfirst, sevenstars, circle8) alongside the existing three,
so `list-sites`/`scrape --site all` finds all 10.

## Context

Modify only: `job_scraper/sites/registry.py`.
Read (do not modify): `job_scraper/sites/synprofs.py`,
`job_scraper/sites/stone_interim.py`, `job_scraper/sites/tender_link.py`,
`job_scraper/sites/harveynash.py`, `job_scraper/sites/headfirst.py`,
`job_scraper/sites/sevenstars.py`, `job_scraper/sites/circle8.py` — to find
each one's exact `SiteAdapter` subclass name and `site_id` (class names
follow `<Site>Adapter`, verify by reading each file).

## Acceptance criteria

- `job_scraper/sites/registry.py` imports and registers all 7 new
  adapters in `SITE_REGISTRY`, alongside the existing 3 (don't remove or
  change the existing 3 entries).
- `uv run python -m job_scraper list-sites` prints exactly 10 site ids,
  sorted: `circle8`, `flexvalue`, `harveynash`, `headfirst`, `hero`,
  `pro_act`, `sevenstars`, `stone_interim`, `synprofs`, `tender_link`.
- Existing tests for the first-wave adapters still pass unchanged.

## Definition of done

Per Appendix A.
