# E3-S05: Wire all three adapters into the registry

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E3-S01`,
`E3-S02`, `E3-S03` (all three adapter modules must already exist) and
`E2-S03` (`SITE_REGISTRY` dict already exists, currently empty).

## Goal

The one place all three Epic-3 adapter modules get registered, so
`list-sites`/`scrape --site all` can find them. Kept as its own story so the
adapter stories never conflict with each other by editing the same file.

Note: a 4th site (freelance.nl) was originally in scope but excluded after
reconnaissance found its robots.txt disallows generic scrapers and its
listing pages are JS-rendered — see `docs/DESIGN_DOC.md`'s "This phase's
three adapters" section. Only 3 adapters exist to wire up.

## Context

Modify only: `job_scraper/sites/registry.py`.
Read (do not modify): `job_scraper/sites/pro_act.py`,
`job_scraper/sites/hero.py`, `job_scraper/sites/flexvalue.py` — to find each
one's exact `SiteAdapter` subclass name and confirm its `site_id` attribute.

Before your change, `registry.py` contains an empty `SITE_REGISTRY:
dict[str, type[SiteAdapter]] = {}`. Each of the three files above exports
one `SiteAdapter` subclass — class names follow the pattern `<Site>Adapter`,
e.g. `ProActAdapter`, but verify by reading each file rather than assuming.

## Acceptance criteria

- `job_scraper/sites/registry.py` imports all three adapter classes and
  populates `SITE_REGISTRY` with one entry per adapter, keyed by that
  adapter's `site_id` class attribute:
  ```python
  from . import pro_act, hero, flexvalue

  SITE_REGISTRY: dict[str, type[SiteAdapter]] = {
      pro_act.<ClassName>.site_id: pro_act.<ClassName>,
      hero.<ClassName>.site_id: hero.<ClassName>,
      flexvalue.<ClassName>.site_id: flexvalue.<ClassName>,
  }
  ```
- `uv run python -m job_scraper list-sites` prints exactly 3 site ids
  (whatever each adapter's `site_id` attribute is set to), sorted.
- Existing tests (`tests/test_adapter_base.py`, `tests/test_pipeline.py`)
  still pass unchanged — this story only adds to the previously-empty dict,
  it doesn't change the `SiteAdapter`/`SITE_REGISTRY` type contracts those
  tests rely on.

## Definition of done

Per Appendix A.
