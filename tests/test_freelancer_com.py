import pytest
from pathlib import Path
from unittest.mock import patch

from job_scraper.core.models import ListingStub
from job_scraper.sites.freelancer_com import FreelancerComAdapter
from job_scraper.sites.base import FetchStrategy


def load_fixture(filename: str) -> bytes:
    fixture_dir = Path("tests/fixtures/freelancer_com")
    return (fixture_dir / filename).read_bytes()


def test_adapter_properties() -> None:
    adapter = FreelancerComAdapter()
    assert adapter.site_id == "freelancer_com"
    assert adapter.base_url == "https://www.freelancer.com"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings() -> None:
    adapter = FreelancerComAdapter()
    listing_html = load_fixture("listing.html")

    # Create a simple "no more pages" HTML to prevent infinite loop
    no_next_page_html = b"""
    <html>
    <body>
    <div class="Pagination">
    </div>
    </body>
    </html>
    """

    call_count = [0]

    def mock_fetch(strategy, url):
        call_count[0] += 1
        if call_count[0] == 1:
            return listing_html
        else:
            return no_next_page_html

    with patch("job_scraper.sites.freelancer_com.fetch_page", side_effect=mock_fetch):
        stubs = list(adapter.list_postings())

    # Should find the astrology testing job
    astrology_stubs = [
        stub
        for stub in stubs
        if "astrology" in stub.title.lower()
        or "astrology" in stub.listing_id.lower()
    ]
    assert len(astrology_stubs) > 0, "Should find astrology testing job"

    # Check the astrology stub
    astrology_stub = astrology_stubs[0]
    assert astrology_stub.title == "Astrology App QA Tester Required"
    assert "astrology-app-tester-required" in astrology_stub.listing_id
    assert "/projects/mobile-app-testing/astrology-app-tester-required" in astrology_stub.detail_url

    # Should have 30 stubs total (one page, 30 entries)
    assert len(stubs) == 30


def test_parse_detail() -> None:
    adapter = FreelancerComAdapter()

    # Create a stub for the detail page
    stub = ListingStub(
        listing_id="astrology-app-tester-required",
        detail_url="https://www.freelancer.com/projects/mobile-app-testing/astrology-app-tester-required",
        title="Astrology App QA Tester Required",
    )

    detail_html = load_fixture("detail_40724221.html")
    posting = adapter.parse_detail(stub, detail_html)

    # Validate title
    assert posting.title == "Astrology App QA Tester Required"

    # Validate rate contains 12500
    assert posting.rate is not None
    assert "12500" in posting.rate
    assert "INR" in posting.rate

    # Validate client is None
    assert posting.client is None

    # Validate description is not empty and contains expected structure
    assert posting.description != ""
    assert "Astrology" in posting.description or "astrology" in posting.description
    assert "\n\n" in posting.description  # Multiple paragraphs
    assert not any(l.startswith("## ") for l in posting.description.splitlines())  # No level-2 headers
    assert any(l.startswith("-") or l.startswith("*") for l in posting.description.splitlines())  # Has list markers
    assert "**" in posting.description  # Has bold text

    # Validate category/skills
    assert posting.category is not None

    # Validate posted_date is present
    assert posting.posted_date is not None
    assert "ago" in posting.posted_date.lower()

    # Validate site_id and listing_id
    assert posting.site_id == "freelancer_com"
    assert posting.listing_id == "astrology-app-tester-required"

    # Validate workplace is Fully Remote (from "Remote project" text)
    assert posting.workplace == "Fully Remote"


def test_source_url_is_human_ad_page() -> None:
    import re

    BAD_FRAGMENTS = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    pattern = re.compile(r"^https://www\.freelancer\.com/projects/[a-z0-9-]+/[a-z0-9-]+$")
    adapter = FreelancerComAdapter()
    stub = ListingStub(
        listing_id="astrology-app-tester-required",
        detail_url="https://www.freelancer.com/projects/mobile-app-testing/astrology-app-tester-required",
        title="Astrology App QA Tester Required",
    )
    posting = adapter.parse_detail(stub, load_fixture("detail_40724221.html"))
    assert posting.source_url == (
        "https://www.freelancer.com/projects/mobile-app-testing/astrology-app-tester-required"
    )
    assert pattern.match(posting.source_url)
    assert not any(b in posting.source_url for b in BAD_FRAGMENTS)


@pytest.mark.parametrize("fixture", ['detail_40724221.html'])
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = FreelancerComAdapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "freelancer_com" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "We have developed an AI-powered astrology application that supports multiple systems" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()
