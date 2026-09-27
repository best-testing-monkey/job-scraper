import pytest
from pathlib import Path

from job_scraper.sites.synprofs import SynprofsAdapter
from job_scraper.core.models import ListingStub


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "synprofs"


@pytest.fixture
def adapter() -> SynprofsAdapter:
    return SynprofsAdapter()


@pytest.fixture
def listing_xml(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "listing.xml").read_bytes()


@pytest.fixture
def detail_html(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "detail_6930.html").read_bytes()


def test_adapter_site_id(adapter: SynprofsAdapter) -> None:
    assert adapter.site_id == "synprofs"


def test_adapter_fetch_strategy(adapter: SynprofsAdapter) -> None:
    from job_scraper.sites.base import FetchStrategy
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings(adapter: SynprofsAdapter, listing_xml: bytes, monkeypatch) -> None:
    # Mock fetch_page to return our fixture
    def mock_fetch_page(strategy, url):
        return listing_xml

    import job_scraper.sites.synprofs
    monkeypatch.setattr(job_scraper.sites.synprofs, "fetch_page", mock_fetch_page)

    # Get all postings
    postings = list(adapter.list_postings())

    # Should have exactly 32 stubs
    assert len(postings) == 32

    # All should be ListingStub instances
    assert all(isinstance(p, ListingStub) for p in postings)

    # Check that at least one has listing_id == "6930"
    listing_ids = [p.listing_id for p in postings]
    assert "6930" in listing_ids

    # All stubs should have non-empty fields
    for stub in postings:
        assert stub.listing_id
        assert stub.detail_url
        assert stub.title


def test_parse_detail_6930(adapter: SynprofsAdapter, detail_html: bytes, monkeypatch) -> None:
    # Create a stub for listing 6930
    stub = ListingStub(
        listing_id="6930",
        detail_url="https://www.synprofs.nl/opdracht/senior-tester-6930/",
        title="Senior Tester",
    )

    # Parse the detail page
    posting = adapter.parse_detail(stub, detail_html)

    # Verify core fields
    assert posting.title == "Senior Tester"
    assert posting.listing_id == "6930"
    assert posting.site_id == "synprofs"

    # Verify client contains either "Dienst ICT Uitvoering" or "DICTU"
    assert posting.client is not None
    assert "Dienst ICT Uitvoering" in posting.client or "DICTU" in posting.client

    # Verify location contains "Assen"
    assert posting.location is not None
    assert "Assen" in posting.location

    # Verify posted_date contains "2026-09-25"
    assert posting.posted_date is not None
    assert "2026-09-25" in posting.posted_date

    # Verify description is non-empty
    assert posting.description
    assert len(posting.description) > 0

    # Verify category and rate are None
    assert posting.category is None
    assert posting.rate is None

    # Verify source_url is set
    assert posting.source_url == stub.detail_url


def test_parse_detail_extra_fields(adapter: SynprofsAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="6930",
        detail_url="https://www.synprofs.nl/opdracht/senior-tester-6930/",
        title="Senior Tester",
    )

    posting = adapter.parse_detail(stub, detail_html)

    # Check that validThrough is in extra_fields
    assert "validThrough" in posting.extra_fields
    assert posting.extra_fields["validThrough"] == "2026-09-30"


def test_parse_detail_hours_and_duration(adapter: SynprofsAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="6930",
        detail_url="https://www.synprofs.nl/opdracht/senior-tester-6930/",
        title="Senior Tester",
    )

    posting = adapter.parse_detail(stub, detail_html)

    # Verify hours is extracted
    assert posting.hours is not None
    assert "36" in posting.hours

    # Verify duration is extracted
    assert posting.duration is not None
    assert "12" in posting.duration or "maanden" in posting.duration
