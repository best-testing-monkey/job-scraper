import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from job_scraper.sites.iamexpat import IamexpatAdapter
from job_scraper.sites.base import FetchStrategy


@pytest.fixture
def adapter():
    return IamexpatAdapter()


@pytest.fixture
def listing_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "iamexpat" / "listing.html"
    with open(fixture_path, "rb") as f:
        return f.read()


@pytest.fixture
def detail_fixture():
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "iamexpat"
        / "detail_tLJWUBCWY1P8MBXMScbwRE.html"
    )
    with open(fixture_path, "rb") as f:
        return f.read()


def test_adapter_properties(adapter):
    assert adapter.site_id == "iamexpat"
    assert adapter.base_url == "https://www.iamexpat.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC
    assert adapter.LISTING_URL == "https://www.iamexpat.nl/career/jobs-netherlands"


def test_list_postings(adapter, listing_fixture):
    """Test that list_postings extracts stubs from the fixture."""

    def mock_fetch(strategy, url, **kwargs):
        # First call returns the listing fixture, second call (page 2) returns empty
        if "?page=1" in url or "?page=" not in url:
            return listing_fixture
        else:
            # Page 2 and beyond return empty (no cards)
            return b"<html></html>"

    with patch("job_scraper.sites.iamexpat.fetch_page", side_effect=mock_fetch):
        stubs = list(adapter.list_postings())

    assert len(stubs) > 0
    # Verify each stub has required fields
    for stub in stubs:
        assert stub.listing_id
        assert stub.detail_url
        assert stub.title
        # Verify listing_id is the trailing path segment
        assert stub.listing_id in stub.detail_url
        assert "/" not in stub.listing_id or ":/" in stub.detail_url  # single segment


def test_list_postings_pagination_terminates(adapter, listing_fixture):
    """Test that pagination loop terminates when a page has no cards."""
    page_count = 0

    def mock_fetch(strategy, url, **kwargs):
        nonlocal page_count
        page_count += 1
        if page_count == 1:
            return listing_fixture
        else:
            # Page 2 returns empty (no cards)
            return b"<html><body></body></html>"

    with patch("job_scraper.sites.iamexpat.fetch_page", side_effect=mock_fetch):
        stubs = list(adapter.list_postings())

    # Should have fetched exactly 2 pages (page 1 with results, page 2 empty)
    assert page_count == 2
    assert len(stubs) > 0


def test_parse_detail(adapter, detail_fixture):
    """Test that parse_detail extracts all required fields from detail fixture."""
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="tLJWUBCWY1P8MBXMScbwRE",
        detail_url="https://www.iamexpat.nl/career/jobs-netherlands/it-technology-positions/junior-devops-engineer-iam-ping-ds-idm/tLJWUBCWY1P8MBXMScbwRE",
        title="Junior DevOps Engineer IAM (Ping DS/IDM)",
    )

    posting = adapter.parse_detail(stub, detail_fixture)

    # Verify required fields per acceptance criteria
    assert posting.title == "Junior DevOps Engineer IAM (Ping DS/IDM)"
    assert posting.client == "Swisscom"
    assert posting.location == "Rotterdam"
    assert posting.posted_date and "September 24, 2026" in posting.posted_date
    assert posting.description  # non-empty
    assert posting.rate is None


def test_parse_detail_category_extracted(adapter, detail_fixture):
    """Test that category is extracted from breadcrumbs."""
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="tLJWUBCWY1P8MBXMScbwRE",
        detail_url="https://example.com",
        title="Test",
    )

    posting = adapter.parse_detail(stub, detail_fixture)
    assert posting.category is not None


def test_parse_detail_duration_and_hours(adapter, detail_fixture):
    """Test that duration and hours are extracted from specs."""
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="tLJWUBCWY1P8MBXMScbwRE",
        detail_url="https://example.com",
        title="Test",
    )

    posting = adapter.parse_detail(stub, detail_fixture)
    # Duration and hours should be extracted from spec items
    # Based on fixture: [1] is duration, [2] is hours
    assert posting.duration is not None
    assert posting.hours is not None
