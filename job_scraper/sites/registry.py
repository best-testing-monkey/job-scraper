from job_scraper.sites.base import SiteAdapter

SITE_REGISTRY: dict[str, type[SiteAdapter]] = {}
