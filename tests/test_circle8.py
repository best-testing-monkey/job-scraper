import pytest
from pathlib import Path
from unittest.mock import patch

from job_scraper.sites.circle8 import Circle8Adapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_circle8_adapter_site_id() -> None:
    adapter = Circle8Adapter()
    assert adapter.site_id == "circle8"


def test_circle8_adapter_base_url() -> None:
    adapter = Circle8Adapter()
    assert adapter.base_url == "https://www.circle8.nl"


def test_circle8_adapter_fetch_strategy() -> None:
    adapter = Circle8Adapter()
    assert adapter.fetch_strategy == FetchStrategy.STEALTH


def test_list_postings() -> None:
    adapter = Circle8Adapter()
    listing_html = Path("tests/fixtures/circle8/listing.html").read_bytes()
    with patch("job_scraper.sites.circle8.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())

    assert len(stubs) == 10
    listing_ids = [stub.listing_id for stub in stubs]
    assert "VNR-85422" in listing_ids


def test_list_postings_absolute_urls() -> None:
    adapter = Circle8Adapter()
    listing_html = Path("tests/fixtures/circle8/listing.html").read_bytes()
    with patch("job_scraper.sites.circle8.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())

    for stub in stubs:
        assert stub.detail_url.startswith("https://www.circle8.nl/opdracht/")


def test_parse_detail_vnr_85422() -> None:
    adapter = Circle8Adapter()
    detail_html = Path("tests/fixtures/circle8/detail_VNR-85422.html").read_bytes()
    stub = ListingStub(
        listing_id="VNR-85422",
        detail_url="https://www.circle8.nl/opdracht/adviseur-ggd-ghor_VNR-85422",
        title="Adviseur GGD-GHOR",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "circle8"
    assert posting.listing_id == "VNR-85422"
    assert posting.title == "Adviseur GGD-GHOR"
    assert posting.location == "Utrecht"
    assert posting.workplace is None
    assert "ICTU" in posting.client
    assert "Openbaar bestuur" in posting.category
    assert posting.hours is not None and "8" in posting.hours
    assert posting.duration is not None and "12" in posting.duration
    assert len(posting.description) > 0
    assert posting.scrape_note is not None
    assert "Page 1" in posting.scrape_note or "page 1" in posting.scrape_note.lower()


def test_parse_detail_description_markdown() -> None:
    adapter = Circle8Adapter()
    detail_html = Path("tests/fixtures/circle8/detail_VNR-85422.html").read_bytes()
    stub = ListingStub(
        listing_id="VNR-85422",
        detail_url="https://www.circle8.nl/opdracht/adviseur-ggd-ghor_VNR-85422",
        title="Adviseur GGD-GHOR",
    )
    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses Markdown formatting
    assert posting.description.strip(), "Description should not be empty"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"


def test_source_url_is_human_ad_page() -> None:
    import re

    BAD_FRAGMENTS = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    pattern = re.compile(r"^https://www\.circle8\.nl/opdracht/[^/?#\s]+_VNR-\d+$")
    adapter = Circle8Adapter()

    listing_html = Path("tests/fixtures/circle8/listing.html").read_bytes()
    with patch("job_scraper.sites.circle8.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert pattern.match(s.detail_url), s.detail_url
        assert not any(b in s.detail_url for b in BAD_FRAGMENTS)

    detail_html = Path("tests/fixtures/circle8/detail_VNR-85422.html").read_bytes()
    stub = next(s for s in stubs if s.listing_id == "VNR-85422")
    posting = adapter.parse_detail(stub, detail_html)
    assert posting.source_url == (
        "https://www.circle8.nl/opdracht/adviseur-ggd-ghor_VNR-85422"
    )
    assert pattern.match(posting.source_url)
    assert not any(b in posting.source_url for b in BAD_FRAGMENTS)


@pytest.mark.parametrize("fixture", ["detail_VNR-85422.html"])
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = Circle8Adapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "circle8" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "De professional heeft de zelfstandige opdracht om het overleg te initiëren" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()


def test_screenshot_hide_selectors_valid() -> None:
    from bs4 import BeautifulSoup

    # E14-S20: live (StealthyFetcher) probe: Cookiebot underlay tints the page,
    # sticky header/logo and sticky vacancy hero overlap the element.
    assert Circle8Adapter.screenshot_hide_selectors == (
        "#CybotCookiebotDialog",
        "#CybotCookiebotDialogBodyUnderlay",
        "#c-header",
        ".c-header__static-logo-wrapper",
        "#sticky-vacancy-hero",
    )
    assert Circle8Adapter.screenshot_selector == "div.c-vacancy-paragraph__body-text"
    html = (Path(__file__).parent / "fixtures" / "circle8/detail_VNR-85422.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    for sel in Circle8Adapter.screenshot_hide_selectors:
        soup.select(sel)
