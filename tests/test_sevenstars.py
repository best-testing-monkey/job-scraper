import pytest
from pathlib import Path
from unittest.mock import patch
from job_scraper.sites.sevenstars import SevenstarsAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_sevenstars_adapter_attributes():
    adapter = SevenstarsAdapter()
    assert adapter.site_id == "sevenstars"
    assert adapter.base_url == "https://www.sevenstars.nl"
    assert adapter.fetch_strategy == FetchStrategy.STEALTH


def test_list_postings():
    adapter = SevenstarsAdapter()
    listing_html = Path("tests/fixtures/sevenstars/listing.html").read_bytes()

    # Create a simple "no more pages" HTML to prevent infinite loop
    no_next_page_html = b"""
    <html>
    <body>
    <div class="c-lister-pagination__wrapper">
    </div>
    </body>
    </html>
    """

    call_count = [0]

    def mock_fetch(strategy, url):
        call_count[0] += 1
        # First call returns page 1, subsequent calls return empty page
        if call_count[0] == 1:
            return listing_html
        else:
            return no_next_page_html

    with patch("job_scraper.sites.sevenstars.fetch_page", side_effect=mock_fetch):
        postings = list(adapter.list_postings())

    assert len(postings) == 10
    listing_ids = [p.listing_id for p in postings]
    assert "7S-004982" in listing_ids

    agile_coach = next((p for p in postings if p.listing_id == "7S-004982"), None)
    assert agile_coach is not None
    assert agile_coach.title == "Agile Coach"
    assert "opdracht/agilecoach_7S-004982" in agile_coach.detail_url


def test_list_postings_with_pagination():
    adapter = SevenstarsAdapter()
    listing_html = Path("tests/fixtures/sevenstars/listing.html").read_bytes()

    # Create a simple "page 2" with no next link to simulate the end of pagination
    page_2_html = b"""
    <html>
    <body>
    <div class="c-vacancy-grid-card">
        <div class="c-vacancy-grid-card__header--left">
            <a href="/opdracht/pagejob_7S-999999"><h3 class="c-vacancy-grid-card__title">Page 2 Job</h3></a>
        </div>
    </div>
    <div class="c-lister-pagination__wrapper">
    </div>
    </body>
    </html>
    """

    call_count = [0]

    def mock_fetch_page_side_effect(strategy, url):
        call_count[0] += 1
        if call_count[0] == 1:
            # First call returns page 1
            return listing_html
        else:
            # Subsequent calls return page 2
            return page_2_html

    with patch("job_scraper.sites.sevenstars.fetch_page", side_effect=mock_fetch_page_side_effect):
        postings = list(adapter.list_postings())

    # Should have 11 postings (10 from page 1 + 1 from page 2)
    assert len(postings) == 11
    listing_ids = [p.listing_id for p in postings]

    # Page 1 should have the agile coach
    assert "7S-004982" in listing_ids

    # Page 2 should have the synthetic job
    assert "7S-999999" in listing_ids

    # Should have made exactly 2 calls
    assert call_count[0] == 2


def test_parse_detail():
    adapter = SevenstarsAdapter()
    detail_html = Path("tests/fixtures/sevenstars/detail_7S-004982.html").read_bytes()
    stub = ListingStub(
        listing_id="7S-004982",
        detail_url="https://www.sevenstars.nl/opdracht/agilecoach_7S-004982",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "sevenstars"
    assert posting.listing_id == "7S-004982"
    assert posting.title == "Agile Coach"
    assert posting.location == "Zwolle"
    assert posting.workplace == "Hybrid"
    assert posting.hours == "40 uren"
    assert posting.duration == "3 Maanden"
    assert posting.client is None
    assert posting.category is None
    assert posting.description != ""
    assert len(posting.description) > 100

    # Rate should be None since the fixture has empty MinValue/MaxValue
    assert posting.rate is None

    # Check that posted_date is set
    assert posting.posted_date is not None
    assert posting.posted_date == "2026-09-25T12:57:23.000Z"

    # Check that validThrough is in extra_fields
    assert "validThrough" in posting.extra_fields


def test_parse_detail_description_markdown() -> None:
    adapter = SevenstarsAdapter()
    detail_html = Path("tests/fixtures/sevenstars/detail_7S-004982.html").read_bytes()
    stub = ListingStub(
        listing_id="7S-004982",
        detail_url="https://www.sevenstars.nl/opdracht/agilecoach_7S-004982",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses html_to_markdown (not plain text stripping)
    # The fixture has malformed HTML (nested <p> tags), so we check for what IS converted
    assert "**" in posting.description, "Description should have bold text"

    # Verify no ## headings (only ### and deeper, or none in this fixture)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


def test_source_url_is_human_ad_page() -> None:
    import re

    adapter = SevenstarsAdapter()
    pattern = r"^https://www\.sevenstars\.nl/opdracht/[a-z0-9-]+_7S-\d+$"
    forbidden = ["/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect"]

    detail_html = Path("tests/fixtures/sevenstars/detail_7S-004982.html").read_bytes()
    stub = ListingStub(
        listing_id="7S-004982",
        detail_url="https://www.sevenstars.nl/opdracht/agilecoach_7S-004982",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)
    assert re.match(pattern, posting.source_url)
    assert not any(f in posting.source_url for f in forbidden)
    # Matches the detail page's own canonical URL.
    assert posting.source_url.encode() in detail_html

    listing_html = Path("tests/fixtures/sevenstars/listing.html").read_bytes()
    empty = b'<html><body><div class="c-lister-pagination__wrapper"></div></body></html>'
    pages = iter([listing_html])
    with patch(
        "job_scraper.sites.sevenstars.fetch_page",
        side_effect=lambda s, u: next(pages, empty),
    ):
        stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert re.match(pattern, s.detail_url), s.detail_url
        assert not any(f in s.detail_url for f in forbidden)


@pytest.mark.parametrize("fixture", ["detail_7S-004982.html"])
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = SevenstarsAdapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "sevenstars" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "Voor een grote organisatie in de regio Zwolle zoeken wij een ervaren" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()


def test_screenshot_hide_selectors_valid() -> None:
    from bs4 import BeautifulSoup

    assert "#CybotCookiebotDialog" in SevenstarsAdapter.screenshot_hide_selectors
    html = (Path(__file__).parent / "fixtures" / "sevenstars/detail_7S-004982.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    for sel in SevenstarsAdapter.screenshot_hide_selectors:
        soup.select(sel)


def test_screenshot_attributes_pinned_live_verified() -> None:
    # E14-S20: verified live through the stealth capture path.
    assert (
        SevenstarsAdapter.screenshot_selector
        == "div.c-vacancy-paragraph__body-text.job-description"
    )
    assert SevenstarsAdapter.screenshot_hide_selectors == (
        "#CybotCookiebotDialog",
        "#CybotCookiebotDialogBodyUnderlay",
        ".c-header__outer-wrapper",
        ".c-vacancy-hero__vacancy-hero-wrapper",
        ".grecaptcha-badge",
    )
