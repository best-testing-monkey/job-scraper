from . import pro_act, hero, flexvalue
from job_scraper.sites.base import SiteAdapter

SITE_REGISTRY: dict[str, type[SiteAdapter]] = {
    pro_act.ProActAdapter.site_id: pro_act.ProActAdapter,
    hero.HeroAdapter.site_id: hero.HeroAdapter,
    flexvalue.FlexValueAdapter.site_id: flexvalue.FlexValueAdapter,
}
