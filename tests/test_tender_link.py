import pytest
from pathlib import Path
from unittest.mock import patch

from job_scraper.sites.tender_link import TenderLinkAdapter


def load_fixture() -> bytes:
    fixture_path = Path(__file__).parent / "fixtures" / "tender_link" / "listing.json"
    return fixture_path.read_bytes()


def test_list_postings_yields_three_stubs() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert len(stubs) == 3


def test_list_postings_first_stub_has_correct_listing_id() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert stubs[0].listing_id == "33345"


def test_list_postings_first_stub_has_correct_detail_url() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert stubs[0].detail_url == "https://tender-link.nl/vacature/brp-specialist-33345/"


def test_parse_detail_returns_correct_title() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.title == "BRP Specialist"
    assert posting.workplace is None


def test_parse_detail_returns_correct_listing_id() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.listing_id == "33345"
    assert posting.workplace is None


def test_parse_detail_returns_correct_site_id() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.site_id == "tender_link"
    assert posting.workplace is None


def test_parse_detail_returns_correct_client() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.client == "gemeente Soest"
    assert posting.workplace is None


def test_parse_detail_returns_correct_category() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.category == "Detachering"
    assert posting.workplace is None


def test_parse_detail_returns_correct_location() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert "Soest" in posting.location or "Utrecht" in posting.location
    assert posting.workplace is None


def test_parse_detail_returns_correct_hours() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.hours == "40"
    assert posting.workplace is None


def test_parse_detail_returns_correct_duration() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.duration == "6 maanden"
    assert posting.workplace is None


def test_parse_detail_returns_correct_rate() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert "68" in posting.rate
    assert "81" in posting.rate
    assert "5400" not in posting.rate
    assert posting.workplace is None


def test_parse_detail_returns_correct_salaried_gross_monthly() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.extra_fields.get("salaried_gross_monthly") == "5400"
    assert posting.workplace is None


def test_parse_detail_returns_non_empty_description() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)
    assert posting.description
    assert len(posting.description) > 0
    assert posting.workplace is None


def test_parse_detail_description_markdown() -> None:
    adapter = TenderLinkAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.tender_link.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[0], None)

    # Verify description uses Markdown formatting (multiple sections joined by blank lines)
    assert "\n\n" in posting.description, "Description should have multiple sections separated by blank lines"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


def test_source_url_is_human_ad_page() -> None:
    import re

    adapter = TenderLinkAdapter()
    pattern = r"^https://tender-link\.nl/vacature/[a-z0-9-]+/$"
    forbidden = ["/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect"]

    with patch("job_scraper.sites.tender_link.fetch_page", return_value=load_fixture()):
        stubs = list(adapter.list_postings())
    for s in stubs:
        assert re.match(pattern, s.detail_url), s.detail_url
        assert not any(f in s.detail_url for f in forbidden)

    posting = adapter.parse_detail(stubs[0], None)
    assert posting.source_url == "https://tender-link.nl/vacature/brp-specialist-33345/"
    assert re.match(pattern, posting.source_url)
    assert not any(f in posting.source_url for f in forbidden)
    # LIMITATION (pinned): the API slug has no SEO suffix, so this URL 301-redirects
    # to the page's canonical URL (detail_33345.html carries ".../brp-specialist-soest-
    # detachering-33345/"). Same ad id, so it still lands on the ad page.
    detail = (
        Path(__file__).parent / "fixtures" / "tender_link" / "detail_33345.html"
    ).read_text()
    canonical = re.search(r'rel="canonical" href="([^"]+)"', detail).group(1)
    assert canonical != posting.source_url
    assert canonical.rstrip("/").rsplit("-", 1)[1] == "33345"
    assert posting.source_url.rstrip("/").rsplit("-", 1)[1] == "33345"


@pytest.mark.parametrize(
    "fixture",
    ["detail_33345.html"],
)
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = TenderLinkAdapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "tender_link" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "Wij zoeken een ervaren professional die snel zijn of haar weg vindt binnen Publiekszaken" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()
