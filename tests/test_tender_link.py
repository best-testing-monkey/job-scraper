from pathlib import Path
from unittest.mock import patch

from job_scraper.sites.tender_link import TenderLinkAdapter


def load_fixture() -> bytes:
    fixture_path = Path(__file__).parent / "fixtures" / "tender_link" / "listing.json"
    return fixture_path.read_bytes()


def test_list_postings_yields_three_stubs() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert len(stubs) == 3


def test_list_postings_first_stub_has_correct_listing_id() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert stubs[0].listing_id == "33345"


def test_list_postings_first_stub_has_correct_detail_url() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert stubs[0].detail_url == "https://tender-link.nl/vacature/brp-specialist-33345/"


def test_parse_detail_returns_correct_title() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.title == "BRP Specialist"


def test_parse_detail_returns_correct_listing_id() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.listing_id == "33345"


def test_parse_detail_returns_correct_site_id() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.site_id == "tender_link"


def test_parse_detail_returns_correct_client() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.client == "gemeente Soest"


def test_parse_detail_returns_correct_category() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.category == "Detachering"


def test_parse_detail_returns_correct_location() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert "Soest" in posting.location or "Utrecht" in posting.location


def test_parse_detail_returns_correct_hours() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.hours == "40"


def test_parse_detail_returns_correct_duration() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.duration == "6 maanden"


def test_parse_detail_returns_correct_rate() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert "68" in posting.rate
    assert "81" in posting.rate
    assert "5400" not in posting.rate


def test_parse_detail_returns_correct_salaried_gross_monthly() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.extra_fields.get("salaried_gross_monthly") == "5400"


def test_parse_detail_returns_non_empty_description() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.description
    assert len(posting.description) > 0
