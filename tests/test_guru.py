import pytest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from job_scraper.sites.guru import GuruAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_guru_adapter_site_id() -> None:
    adapter = GuruAdapter()
    assert adapter.site_id == "guru"


def test_guru_adapter_fetch_strategy() -> None:
    adapter = GuruAdapter()
    assert adapter.fetch_strategy == FetchStrategy.STEALTH


def test_list_postings() -> None:
    adapter = GuruAdapter()
    listing_html = Path("tests/fixtures/guru/listing.html").read_bytes()

    def mock_fetch(strategy: Any, url: str, **kwargs: Any) -> bytes:
        # Only return the HTML for the first page
        if "pg/" in url:
            # Return empty page for page 2 (no records, no pagination)
            return b"<html><body></body></html>"
        return listing_html

    with patch("job_scraper.sites.guru.fetch_page", side_effect=mock_fetch):
        stubs = list(adapter.list_postings())

    assert len(stubs) > 0
    listing_ids = [stub.listing_id for stub in stubs]
    assert "2120954" in listing_ids


def test_list_postings_absolute_urls() -> None:
    adapter = GuruAdapter()
    listing_html = Path("tests/fixtures/guru/listing.html").read_bytes()

    def mock_fetch(strategy: Any, url: str, **kwargs: Any) -> bytes:
        # Only return the HTML for the first page
        if "pg/" in url:
            # Return empty page for page 2 (no records, no pagination)
            return b"<html><body></body></html>"
        return listing_html

    with patch("job_scraper.sites.guru.fetch_page", side_effect=mock_fetch):
        stubs = list(adapter.list_postings())

    for stub in stubs:
        assert stub.detail_url.startswith("https://www.guru.com/jobs/")


def test_parse_detail_2101732() -> None:
    adapter = GuruAdapter()
    detail_html = Path("tests/fixtures/guru/detail_2101732.html").read_bytes()
    stub = ListingStub(
        listing_id="2101732",
        detail_url="https://www.guru.com/jobs/automation-test-selenium-with-c/2101732",
        title="Automation Test Selenium with C#",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "guru"
    assert posting.listing_id == "2101732"
    assert posting.title == "Automation Test Selenium with C#"
    assert posting.rate is not None and "250-$500" in posting.rate
    assert posting.category is not None and ("QA" in posting.category or "Testing" in posting.category)
    assert posting.client is None
    assert posting.location == "India"
    assert posting.workplace == "Fully Remote"
    assert len(posting.description) > 0
    assert "Show more" not in posting.description
    assert "skills" in posting.extra_fields
    assert len(posting.extra_fields["skills"]) > 0

    # Verify description structure - has multiple paragraphs
    assert "\n\n" in posting.description

    # Check for list items
    lines = posting.description.splitlines()
    has_list = any(l.startswith("1. ") or l.startswith("- ") for l in lines)
    assert has_list, "Description should have list items"

    # Check no level-2 headings (reserved for page structure)
    assert not any(l.startswith("## ") for l in lines)

    # Check for trailing whitespace (except hard breaks)
    for line in lines:
        if not line.endswith("  "):
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"


def test_source_url_is_human_ad_page() -> None:
    import re

    _FORBIDDEN = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    shape = re.compile(r"^https://www\.guru\.com/jobs/[a-z0-9-]+/\d+$")
    adapter = GuruAdapter()
    listing_html = Path("tests/fixtures/guru/listing.html").read_bytes()

    def mock_fetch(strategy: Any, url: str, **kwargs: Any) -> bytes:
        if "pg/" in url:
            return b"<html><body></body></html>"
        return listing_html

    with patch("job_scraper.sites.guru.fetch_page", side_effect=mock_fetch):
        stubs = list(adapter.list_postings())
    assert stubs
    for stub in stubs:
        assert shape.match(stub.detail_url), stub.detail_url
        assert "SearchUrl" not in stub.detail_url

    detail_html = Path("tests/fixtures/guru/detail_2101732.html").read_bytes()
    stub = ListingStub(
        listing_id="2101732",
        detail_url="https://www.guru.com/jobs/automation-test-selenium-with-c/2101732",
        title="Automation Test Selenium with C#",
    )
    posting = adapter.parse_detail(stub, detail_html)
    # Matches the detail fixture's <link rel="canonical"> / og:url.
    assert posting.source_url == (
        "https://www.guru.com/jobs/automation-test-selenium-with-c/2101732"
    )
    assert shape.match(posting.source_url)
    assert not any(bad in posting.source_url for bad in _FORBIDDEN)


@pytest.mark.parametrize("fixture", ['detail_2101732.html'])
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = GuruAdapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "guru" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "Test case Automation using Selenium framework" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()
