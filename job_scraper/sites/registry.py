from . import (
    pro_act,
    hero,
    flexvalue,
    synprofs,
    stone_interim,
    tender_link,
    harveynash,
    headfirst,
    sevenstars,
    circle8,
)
from job_scraper.sites.base import SiteAdapter

SITE_REGISTRY: dict[str, type[SiteAdapter]] = {
    pro_act.ProActAdapter.site_id: pro_act.ProActAdapter,
    hero.HeroAdapter.site_id: hero.HeroAdapter,
    flexvalue.FlexValueAdapter.site_id: flexvalue.FlexValueAdapter,
    synprofs.SynprofsAdapter.site_id: synprofs.SynprofsAdapter,
    stone_interim.StoneInterimAdapter.site_id: stone_interim.StoneInterimAdapter,
    tender_link.TenderLinkAdapter.site_id: tender_link.TenderLinkAdapter,
    harveynash.HarveyNashAdapter.site_id: harveynash.HarveyNashAdapter,
    headfirst.HeadfirstAdapter.site_id: headfirst.HeadfirstAdapter,
    sevenstars.SevenstarsAdapter.site_id: sevenstars.SevenstarsAdapter,
    circle8.Circle8Adapter.site_id: circle8.Circle8Adapter,
}
