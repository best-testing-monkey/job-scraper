from pathlib import Path
from unittest.mock import patch
from job_scraper.sites.pro_act import ProActAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_pro_act_adapter_attributes():
    adapter = ProActAdapter()
    assert adapter.site_id == "pro_act"
    assert adapter.base_url == "https://pro-act.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings():
    adapter = ProActAdapter()
    listing_html = Path("tests/fixtures/pro_act/listing.html").read_text()
    with patch("job_scraper.sites.pro_act.fetch_page", return_value=listing_html):
        postings = list(adapter.list_postings())
    assert len(postings) >= 1
    listing_ids = [p.listing_id for p in postings]
    assert "8887" in listing_ids
    agile_coach = next((p for p in postings if p.listing_id == "8887"), None)
    assert agile_coach is not None
    assert agile_coach.title == "Agile Coach"
    assert "agile-coach-8887" in agile_coach.detail_url


def test_parse_detail():
    adapter = ProActAdapter()
    detail_html = Path("tests/fixtures/pro_act/detail_8887.html").read_text()
    stub = ListingStub(
        listing_id="8887",
        detail_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)
    assert posting.site_id == "pro_act"
    assert posting.listing_id == "8887"
    assert posting.title == "Agile Coach"
    assert posting.hours == "40"
    assert posting.posted_date == "25 september 2026"
    assert posting.extra_fields["Verloopt"] == "30 september 2026"
    assert posting.description != ""
    assert len(posting.description) > 100
    assert posting.workplace == "Hybrid"


def test_parse_detail_client_location_rate():
    adapter = ProActAdapter()
    detail_html = Path("tests/fixtures/pro_act/detail_8887.html").read_text()
    stub = ListingStub(
        listing_id="8887",
        detail_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)
    assert posting.client is not None
    assert "Universiteit van Amsterdam" in posting.client
    assert posting.location == "hybride"
    assert posting.workplace == "Hybrid"
    assert posting.rate == "marktconform"


def test_parse_detail_description_markdown():
    adapter = ProActAdapter()
    detail_html = Path("tests/fixtures/pro_act/detail_8887.html").read_text()
    stub = ListingStub(
        listing_id="8887",
        detail_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses Markdown formatting
    assert "\n\n" in posting.description, "Description should have multiple paragraphs"
    assert any(l.startswith("- ") for l in posting.description.splitlines()), "Description should have list items"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"

    # Verify form boilerplate is not included
    assert "Interesse?" not in posting.description, "Description should not include form sections"
    assert "loondienst" not in posting.description, "Description should not include form options"


def test_source_url_is_human_ad_page():
    import re

    pattern = re.compile(r"^https://pro-act\.nl/vacatures/[a-z0-9-]+-\d+/$")
    bad_parts = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    adapter = ProActAdapter()

    detail_html = Path("tests/fixtures/pro_act/detail_8887.html").read_text()
    stub = ListingStub(
        listing_id="8887",
        detail_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
    )
    posting = adapter.parse_detail(stub, detail_html)
    assert pattern.match(posting.source_url)
    assert not any(b in posting.source_url for b in bad_parts)

    listing_html = Path("tests/fixtures/pro_act/listing.html").read_text()
    with patch("job_scraper.sites.pro_act.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert pattern.match(s.detail_url), s.detail_url
        assert not any(b in s.detail_url for b in bad_parts)


def test_screenshot_selector_wrapper_and_hidden_form() -> None:
    from bs4 import BeautifulSoup

    html = Path("tests/fixtures/pro_act/detail_8887.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    els = soup.select(ProActAdapter.screenshot_selector)
    assert len(els) == 1
    assert els[0].select_one("div.contact-info") is not None
    assert "div.contact-info" in ProActAdapter.screenshot_hide_selectors
    for sel in ProActAdapter.screenshot_hide_selectors:
        soup.select(sel)
