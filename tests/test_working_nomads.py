from pathlib import Path
from unittest.mock import patch

from job_scraper.sites.working_nomads import WorkingNomadsAdapter
from job_scraper.core.models import ListingStub
from job_scraper.sites.base import FetchStrategy


def load_fixture() -> bytes:
    fixture_path = Path(__file__).parent / "fixtures" / "working_nomads" / "listing.json"
    return fixture_path.read_bytes()


def test_adapter_site_id() -> None:
    adapter = WorkingNomadsAdapter()
    assert adapter.site_id == "working_nomads"


def test_adapter_base_url() -> None:
    adapter = WorkingNomadsAdapter()
    assert adapter.base_url == "https://www.workingnomads.com"


def test_adapter_fetch_strategy() -> None:
    adapter = WorkingNomadsAdapter()
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings_yields_five_stubs() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert len(stubs) == 5


def test_list_postings_yields_listing_stubs() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    for stub in stubs:
        assert isinstance(stub, ListingStub)
        assert stub.listing_id
        assert stub.detail_url
        assert stub.title


def test_list_postings_qa_engineer_stub() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())

    qa_stub = stubs[2]
    assert qa_stub.listing_id == "1843242"
    assert qa_stub.title == "Senior QA Automation Engineer"
    assert qa_stub.detail_url == "https://www.workingnomads.com/job/go/1843242/"


def test_parse_detail_returns_correct_site_id() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.site_id == "working_nomads"


def test_parse_detail_returns_correct_listing_id() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.listing_id == "1843242"


def test_parse_detail_returns_correct_title() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.title == "Senior QA Automation Engineer"


def test_parse_detail_returns_correct_client() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.client == "Proxify"


def test_parse_detail_returns_correct_location() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.location == "Time zone: CET (+/- 3 hours)"


def test_parse_detail_returns_qa_tags_in_category() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert "qa" in posting.category.lower()
    assert "playwright" in posting.category.lower()
    assert "selenium" in posting.category.lower()
    assert "test automation" in posting.category.lower()


def test_parse_detail_returns_non_empty_description() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.description
    assert len(posting.description) > 0
    assert "Senior QA Automation Engineer" in posting.description or "Proxify" in posting.description


def test_parse_detail_returns_correct_posted_date() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.posted_date == "2026-09-07T14:40:19-04:00"


def test_parse_detail_hours_is_none() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.hours is None


def test_parse_detail_rate_is_none() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.rate is None


def test_parse_detail_duration_is_none() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.duration is None


def test_parse_detail_stores_category_name_in_extra_fields() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.extra_fields.get("category_name") == "Development"


def test_parse_detail_ignores_page_argument() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting1 = adapter.parse_detail(stubs[2], b"ignored page 1")
    posting2 = adapter.parse_detail(stubs[2], b"ignored page 2")
    assert posting1.title == posting2.title
    assert posting1.client == posting2.client
