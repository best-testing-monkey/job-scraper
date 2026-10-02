from pathlib import Path
from unittest.mock import patch

from job_scraper.sites.planet_interim import PlanetInterimAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_planet_interim_adapter_site_id() -> None:
    adapter = PlanetInterimAdapter()
    assert adapter.site_id == "planet_interim"


def test_planet_interim_adapter_base_url() -> None:
    adapter = PlanetInterimAdapter()
    assert adapter.base_url == "https://planetinterim.nl"


def test_planet_interim_adapter_fetch_strategy() -> None:
    adapter = PlanetInterimAdapter()
    assert adapter.fetch_strategy == FetchStrategy.STEALTH


def test_list_postings() -> None:
    adapter = PlanetInterimAdapter()
    listing_html = Path("tests/fixtures/planet_interim/listing.html").read_bytes()
    with patch("job_scraper.sites.planet_interim.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())

    assert len(stubs) > 0
    listing_ids = [stub.listing_id for stub in stubs]
    assert "539572" in listing_ids


def test_list_postings_absolute_urls() -> None:
    adapter = PlanetInterimAdapter()
    listing_html = Path("tests/fixtures/planet_interim/listing.html").read_bytes()
    with patch("job_scraper.sites.planet_interim.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())

    for stub in stubs:
        assert stub.detail_url.startswith("https://planetinterim.nl/")


def test_parse_detail_539572() -> None:
    adapter = PlanetInterimAdapter()
    detail_html = Path("tests/fixtures/planet_interim/detail_539572.html").read_bytes()
    stub = ListingStub(
        listing_id="539572",
        detail_url="https://planetinterim.nl/beleidsadviseur-digitaal-veilig/539572/p13/default.html",
        title="Beleidsadviseur Digitaal Veilig Onderwijs (DVO)",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "planet_interim"
    assert posting.listing_id == "539572"
    assert "Beleidsadviseur" in posting.title
    assert posting.location == "Zoetermeer"
    assert posting.workplace is None
    assert posting.hours == "24"
    assert posting.client is None
    assert posting.description == ""
    assert posting.scrape_note is not None
    assert "membership" in posting.scrape_note.lower() or "login" in posting.scrape_note.lower()
