from pathlib import Path
from unittest.mock import patch, MagicMock

from job_scraper.sites.stone_interim import StoneInterimAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


LINK_4893 = "https://www.stone-interim.nl/opdrachten/id/4893/Interim+Supply+Chain+Manager/Interim/"


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

    adapter._link_cache["4893"] = LINK_4893
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


def test_parse_detail_description_markdown() -> None:
    detail_data = load_fixture_bytes("detail_4893_api_GetVacancy.json")
    adapter = StoneInterimAdapter()

    stub = ListingStub(
        listing_id="4893",
        detail_url="https://www.stone-interim.nl/api/v1/WordPress/GetVacancy/4893",
        title="Interim Supply Chain Manager",
    )

    adapter._link_cache["4893"] = LINK_4893
    posting = adapter.parse_detail(stub, detail_data)

    # Verify description uses Markdown formatting (multiple sections joined by blank lines)
    assert "\n\n" in posting.description, "Description should have multiple sections separated by blank lines"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


def _list_stubs(adapter: StoneInterimAdapter) -> list[ListingStub]:
    mock_response = MagicMock()
    mock_response.body = load_fixture_bytes("listing_api_GetOverviewItems.json")
    with patch("job_scraper.sites.stone_interim.Fetcher.post", return_value=mock_response):
        return list(adapter.list_postings())


def test_list_postings_detail_url_stays_api() -> None:
    stubs = _list_stubs(StoneInterimAdapter())
    assert stubs
    assert all("/api/v1/WordPress/GetVacancy/" in s.detail_url for s in stubs)


def test_source_url_is_exact_link_url_for_all_items() -> None:
    import json

    adapter = StoneInterimAdapter()
    stubs = _list_stubs(adapter)
    items = json.loads(load_fixture_bytes("listing_api_GetOverviewItems.json"))["Items"]
    assert len(items) == 24 and len(stubs) == 24
    detail = load_fixture_bytes("detail_4893_api_GetVacancy.json")
    by_id = {s.listing_id: s for s in stubs}
    for item in items:
        listing_id = item["LinkUrl"].split("/id/")[1].split("/")[0]
        posting = adapter.parse_detail(by_id[listing_id], detail)
        assert posting.source_url == adapter.base_url + item["LinkUrl"]
        assert "/api/" not in posting.source_url
        assert "GetVacancy" not in posting.source_url


def test_parse_detail_4893_source_url_human() -> None:
    adapter = StoneInterimAdapter()
    stub = next(s for s in _list_stubs(adapter) if s.listing_id == "4893")
    posting = adapter.parse_detail(stub, load_fixture_bytes("detail_4893_api_GetVacancy.json"))
    assert posting.source_url == LINK_4893


def test_parse_detail_without_listing_raises() -> None:
    import pytest

    stub = ListingStub(
        listing_id="4893",
        detail_url="https://www.stone-interim.nl/api/v1/WordPress/GetVacancy/4893",
        title="x",
    )
    with pytest.raises(ValueError, match="LinkUrl"):
        StoneInterimAdapter().parse_detail(stub, load_fixture_bytes("detail_4893_api_GetVacancy.json"))


def test_screenshot_selector_matches_rendered_fixture() -> None:
    from bs4 import BeautifulSoup

    html = (Path(__file__).parent / "fixtures" / "stone_interim" / "rendered_3783.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    els = soup.select(StoneInterimAdapter.screenshot_selector)
    assert len(els) == 1
    text = els[0].get_text(" ", strip=True)
    assert "Dan is onze opdrachtgever in regio Tilburg op zoek naar jou!" in text
    # block__header are the ad's own section headings, not the page header
    assert not els[0].select("nav, footer, form")
    assert not [h for h in els[0].select("header") if "block__header" not in h.get("class", [])]
    assert "cookie" not in text.lower()
    assert "section.cookiebar" in StoneInterimAdapter.screenshot_hide_selectors
    for sel in StoneInterimAdapter.screenshot_hide_selectors:
        soup.select(sel)
