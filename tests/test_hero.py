import pytest
from pathlib import Path

from job_scraper.sites.hero import HeroAdapter
from job_scraper.sites.base import FetchStrategy


@pytest.fixture
def listing_html() -> str:
    fixture_path = Path(__file__).parent / "fixtures" / "hero" / "listing.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def detail_html() -> str:
    fixture_path = Path(__file__).parent / "fixtures" / "hero" / "detail_e98187b8.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def adapter() -> HeroAdapter:
    return HeroAdapter()


class TestHeroAdapterConfig:
    def test_site_id(self, adapter: HeroAdapter) -> None:
        assert adapter.site_id == "hero"

    def test_base_url(self, adapter: HeroAdapter) -> None:
        assert adapter.base_url == "https://hero.eu"

    def test_fetch_strategy(self, adapter: HeroAdapter) -> None:
        assert adapter.fetch_strategy == FetchStrategy.STATIC


class TestHeroListPostings:
    def test_list_postings_yields_stubs(
        self, adapter: HeroAdapter, listing_html: str
    ) -> None:
        stubs = list(adapter.list_postings(listing_html))
        assert len(stubs) >= 1

    def test_list_postings_has_absolute_urls(
        self, adapter: HeroAdapter, listing_html: str
    ) -> None:
        stubs = list(adapter.list_postings(listing_html))
        for stub in stubs:
            assert stub.detail_url.startswith("https://")

    def test_list_postings_includes_e98187b8(
        self, adapter: HeroAdapter, listing_html: str
    ) -> None:
        stubs = list(adapter.list_postings(listing_html))
        listing_ids = [stub.listing_id for stub in stubs]
        assert "e98187b8" in listing_ids


class TestHeroParseDetail:
    def test_parse_detail_cloud_engineer(
        self, adapter: HeroAdapter, detail_html: str
    ) -> None:
        from job_scraper.core.models import ListingStub

        stub = ListingStub(
            listing_id="e98187b8",
            detail_url="https://hero.eu/interim-opdrachten/cloud-engineer-e98187b8",
            title="Cloud Engineer",
        )
        posting = adapter.parse_detail(stub, detail_html)

        assert posting.title == "Cloud Engineer"
        assert posting.listing_id == "e98187b8"
        assert posting.site_id == "hero"
        assert posting.location == "Maasland"
        assert posting.hours == "36 uur/week"
        assert (
            "Cloud Engineer voor het programma Grensverleggende IT"
            in posting.description
        )
