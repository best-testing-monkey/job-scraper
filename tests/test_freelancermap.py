from pathlib import Path
from unittest.mock import patch

from job_scraper.core.models import ListingStub
from job_scraper.sites.base import FetchStrategy
from job_scraper.sites.freelancermap import FreelancermapAdapter

LISTING_FIXTURE = Path("tests/fixtures/freelancermap/listing.html")
DETAIL_FIXTURE = Path(
    "tests/fixtures/freelancermap/"
    "detail_test-automation-consultant-m-w-d-playwright.html"
)
TARGET_ID = "3051456"
TARGET_TITLE = "Test Automation Consultant (m/w/d) Playwright"


def _listing_bytes() -> bytes:
    return LISTING_FIXTURE.read_bytes()


def _detail_bytes() -> bytes:
    return DETAIL_FIXTURE.read_bytes()


def test_freelancermap_adapter_attributes() -> None:
    adapter = FreelancermapAdapter()
    assert adapter.site_id == "freelancermap"
    assert adapter.base_url == "https://www.freelancermap.de"
    assert adapter.fetch_strategy == FetchStrategy.STEALTH
    assert adapter.LISTING_URL == "https://www.freelancermap.de/projekte?query=Playwright"


def test_list_postings() -> None:
    adapter = FreelancermapAdapter()
    with patch(
        "job_scraper.sites.freelancermap.fetch_page", return_value=_listing_bytes()
    ):
        stubs = list(adapter.list_postings())

    assert 20 <= len(stubs) <= 25

    listing_ids = [stub.listing_id for stub in stubs]
    assert TARGET_ID in listing_ids

    target_stub = next(stub for stub in stubs if stub.listing_id == TARGET_ID)
    assert target_stub.title == TARGET_TITLE
    assert target_stub.detail_url == (
        "https://www.freelancermap.de/projekt/"
        "test-automation-consultant-m-w-d-playwright"
    )

    for stub in stubs:
        assert stub.detail_url.startswith("https://www.freelancermap.de/projekt/")


def test_parse_detail_test_automation_consultant() -> None:
    adapter = FreelancermapAdapter()
    stub = ListingStub(
        listing_id=TARGET_ID,
        detail_url=(
            "https://www.freelancermap.de/projekt/"
            "test-automation-consultant-m-w-d-playwright"
        ),
        title=TARGET_TITLE,
    )

    posting = adapter.parse_detail(stub, _detail_bytes())

    assert posting.site_id == "freelancermap"
    assert posting.listing_id == TARGET_ID
    assert "Test Automation Consultant" in posting.title
    assert posting.duration is not None and "3 Monate" in posting.duration
    assert posting.hours is not None and "100%" in posting.hours
    assert posting.category is not None and "Playwright" in posting.category
    assert len(posting.description) > 0
    assert posting.scrape_note
    assert "paginat" in posting.scrape_note.lower()
    assert posting.client is None
    assert posting.rate is None


def test_parse_detail_extra_fields_and_location() -> None:
    adapter = FreelancermapAdapter()
    stub = ListingStub(
        listing_id=TARGET_ID,
        detail_url=(
            "https://www.freelancermap.de/projekt/"
            "test-automation-consultant-m-w-d-playwright"
        ),
        title=TARGET_TITLE,
    )

    posting = adapter.parse_detail(stub, _detail_bytes())

    assert posting.location is not None and "München" in posting.location
    assert posting.extra_fields.get("contract_type") == "Freiberuflich"
    assert posting.extra_fields.get("start_date") == "ab sofort"
    assert posting.posted_date == "23.09.2026"
