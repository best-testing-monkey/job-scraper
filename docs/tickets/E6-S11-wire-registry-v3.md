# E6-S11: Wire third-wave adapters into the registry

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E6-S01` through `E6-S10` (all ten third-wave adapter modules must already exist) and the existing `job_scraper/sites/registry.py` (currently has 10 sites registered from the first two waves).

## Goal

Register the third-wave adapters (iamexpat, djinni, arc_dev, freelancer_com, guru, planet_interim, ictergezocht, wearedevelopers, working_nomads, freelancermap) alongside the existing 10, so `list-sites`/`scrape --site all` finds all 20.

## Context

Modify only: `job_scraper/sites/registry.py`.
Read (do not modify): each of the 10 new adapter files listed above, to find each one's exact `SiteAdapter` subclass name and `site_id` (verify by reading, don't assume from the ticket names).

## Acceptance criteria

- `job_scraper/sites/registry.py` imports and registers all 10 new adapters in `SITE_REGISTRY`, alongside the existing 10 (don't remove or change those).
- `uv run python -m job_scraper list-sites` prints exactly 20 site ids, sorted.
- Existing tests for all prior adapters still pass unchanged.

## Definition of done

Per Appendix A.
