from pathlib import Path
from unittest.mock import patch, MagicMock

from job_scraper.sites.stone_interim import StoneInterimAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def load_fixture_bytes(filename: str) -> bytes:
    fixture_path = Path(__file__).parent / "fixtures" / "stone_interim" / filename
    return fixture_path.read_bytes()


def test_adapter_properties() -> None:
    adapter = StoneInterimAdapter()
    assert adapter.site_id == "stone_interim"
    assert adapter.base_url == "https://www.stone-interim.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings_yields_stubs() -> None:
    listing_data = load_fixture_bytes("listing_api_GetOverviewItems.json")
    adapter = StoneInterimAdapter()

    mock_response = MagicMock()
    mock_response.body = listing_data

    with patch("job_scraper.sites.stone_interim.Fetcher.post", return_value=mock_response):
        stubs = list(adapter.list_postings())

    assert len(stubs) >= 24


def test_list_postings_includes_4893() -> None:
    listing_data = load_fixture_bytes("listing_api_GetOverviewItems.json")
    adapter = StoneInterimAdapter()

    mock_response = MagicMock()
    mock_response.body = listing_data

    with patch("job_scraper.sites.stone_interim.Fetcher.post", return_value=mock_response):
        stubs = list(adapter.list_postings())

    listing_ids = [stub.listing_id for stub in stubs]
    assert "4893" in listing_ids


def test_parse_detail_4893() -> None:
    detail_data = load_fixture_bytes("detail_4893_api_GetVacancy.json")
    adapter = StoneInterimAdapter()

    stub = ListingStub(
        listing_id="4893",
        detail_url="https://www.stone-interim.nl/api/v1/WordPress/GetVacancy/4893",
        title="Interim Supply Chain Manager",
    )

    posting = adapter.parse_detail(stub, detail_data)

    assert posting.title == "Interim Supply Chain Manager"
    assert posting.listing_id == "4893"
    assert posting.site_id == "stone_interim"
    assert posting.client is None
    assert posting.hours == "40"
    assert posting.location == "Noord Brabant"
    assert posting.workplace is None
    assert posting.category == "Technology"
    assert posting.rate is None
    assert len(posting.description) > 0
