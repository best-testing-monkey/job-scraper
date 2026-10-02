import pytest
from pathlib import Path
from unittest.mock import patch
from job_scraper.sites.harveynash import HarveyNashAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_harveynash_adapter_attributes():
    adapter = HarveyNashAdapter()
    assert adapter.site_id == "harveynash"
    assert adapter.base_url == "https://www.harveynash.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings():
    adapter = HarveyNashAdapter()
    sitemap_xml = Path("tests/fixtures/harveynash/sitemap.xml").read_text()
    with patch("job_scraper.sites.harveynash.fetch_page", return_value=sitemap_xml):
        postings = list(adapter.list_postings())

    # Should have at least one job posting
    assert len(postings) >= 1

    # Should have the specific job we're testing
    listing_ids = [p.listing_id for p in postings]
    assert "299204" in listing_ids

    # Check the specific job posting
    job_299204 = next((p for p in postings if p.listing_id == "299204"), None)
    assert job_299204 is not None
    assert job_299204.detail_url == "https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert"

    # Should exclude non-job URLs
    all_urls = [p.detail_url for p in postings]
    assert not any("/vacatures/internal" in url for url in all_urls)
    assert not any("/vacatures/thank-you-for-applying" in url for url in all_urls)
    assert not any("/vacatures/thank-you-for-submitting-cv" in url for url in all_urls)


def test_parse_detail():
    adapter = HarveyNashAdapter()
    detail_html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    stub = ListingStub(
        listing_id="299204",
        detail_url="https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert",
        title="Expert (gas)regelvermogen Weert",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "harveynash"
    assert posting.listing_id == "299204"
    assert posting.title == "Expert (gas)regelvermogen Weert"
    assert posting.description != ""
    assert len(posting.description) > 100
    assert posting.workplace == "Hybrid"


def test_parse_detail_full_fields():
    adapter = HarveyNashAdapter()
    detail_html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    stub = ListingStub(
        listing_id="299204",
        detail_url="https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert",
        title="Expert (gas)regelvermogen Weert",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.client == "Enexis"
    assert "Techniek" in posting.category or "Projectbeheersing" in posting.category
    assert posting.location == "Weert, Limburg"
    assert posting.workplace == "Hybrid"
    assert posting.hours == "Fulltime"
    assert posting.rate == "Bespreekbaar"
    assert posting.extra_fields.get("employment_type") == "Interim"
    assert posting.extra_fields.get("expires_at") == "2026-10-02T23:59:59.999Z"


def test_parse_detail_description_markdown():
    adapter = HarveyNashAdapter()
    detail_html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    stub = ListingStub(
        listing_id="299204",
        detail_url="https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert",
        title="Expert (gas)regelvermogen Weert",
    )
    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses Markdown formatting
    assert "\n\n" in posting.description, "Description should have multiple paragraphs"
    assert "**" in posting.description, "Description should have bold text"
    assert "- " in posting.description, "Description should have list items"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


def test_source_url_is_human_ad_page():
    import re

    _FORBIDDEN = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    shape = re.compile(r"^https://www\.harveynash\.nl/vacatures/\d+-[^/?#]+$")
    adapter = HarveyNashAdapter()
    sitemap_xml = Path("tests/fixtures/harveynash/sitemap.xml").read_text()
    with patch("job_scraper.sites.harveynash.fetch_page", return_value=sitemap_xml):
        stubs = list(adapter.list_postings())
    assert stubs
    for stub in stubs:
        assert shape.match(stub.detail_url), stub.detail_url

    stub = next(s for s in stubs if s.listing_id == "299204")
    detail_html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    posting = adapter.parse_detail(stub, detail_html)
    # Matches the detail fixture's <link rel="canonical"> / og:url.
    assert posting.source_url == (
        "https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert"
    )
    assert not any(bad in posting.source_url for bad in _FORBIDDEN)

    # Error path (no __NEXT_DATA__) still keeps the real ad URL.
    fallback = adapter.parse_detail(stub, "<html><body></body></html>")
    assert fallback.source_url == posting.source_url


@pytest.mark.parametrize(
    "fixture",
    ["detail_299204.html"],
)
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = HarveyNashAdapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "harveynash" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "Je werkt samen met je collega's van het Congestie Office" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()


def test_screenshot_hide_selectors_valid() -> None:
    from bs4 import BeautifulSoup

    assert HarveyNashAdapter.screenshot_hide_selectors == ("div.social-share",)
    html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    post = soup.select_one(HarveyNashAdapter.screenshot_selector)
    assert post.select_one("div.social-share") is not None
