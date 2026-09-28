import pytest
from unittest.mock import patch

from job_scraper.sites.wearedevelopers import WearedevelopersAdapter


@pytest.fixture
def adapter() -> WearedevelopersAdapter:
    return WearedevelopersAdapter()


@pytest.fixture
def listing_html() -> bytes:
    with open("tests/fixtures/wearedevelopers/listing.html", "rb") as f:
        return f.read()


@pytest.fixture
def detail_html() -> bytes:
    with open("tests/fixtures/wearedevelopers/detail_2904764.html", "rb") as f:
        return f.read()


def test_list_postings(adapter: WearedevelopersAdapter, listing_html: bytes) -> None:
    with patch("job_scraper.sites.wearedevelopers.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())

        assert len(stubs) > 0
        assert len(stubs) == 24

        ids = [stub.listing_id for stub in stubs]
        assert "2904764" in ids

        stub_2904764 = next(s for s in stubs if s.listing_id == "2904764")
        assert stub_2904764.title
        assert "/jobs/ext/2904764" in stub_2904764.detail_url


def test_parse_detail_basic(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "wearedevelopers"
    assert posting.listing_id == "2904764"
    assert posting.title == "Senior Qa Testing Engineer"
    assert posting.client == "AILY LABS"
    assert posting.location == "Barcelona, Spain"
    assert posting.posted_date == "2026-09-14"
    assert posting.rate is None
    assert posting.hours is None
    assert posting.duration is None


def test_parse_detail_description(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.description
    assert len(posting.description) > 0
    assert "Mission" in posting.description or "QA" in posting.description


def test_parse_detail_scrape_note(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.scrape_note
    assert "pagination" in posting.scrape_note.lower()
    assert "Hotwire" in posting.scrape_note or "Turbo" in posting.scrape_note


def test_parse_detail_category(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.category
    assert "Testing" in posting.category or "JavaScript" in posting.category


def test_adapter_constants(adapter: WearedevelopersAdapter) -> None:
    assert adapter.site_id == "wearedevelopers"
    assert adapter.base_url == "https://www.wearedevelopers.com"
    assert adapter.fetch_strategy.value == "stealth"
