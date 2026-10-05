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

    # Verify workplace is classified as Hybrid
    assert posting.workplace == "Hybrid"

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

    # Verify workplace is Hybrid
    assert posting.workplace == "Hybrid"


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

    # Verify workplace is Hybrid
    assert posting.workplace == "Hybrid"


def test_parse_detail_description_markdown(adapter: SynprofsAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="6930",
        detail_url="https://www.synprofs.nl/opdracht/senior-tester-6930/",
        title="Senior Tester",
    )

    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses Markdown formatting
    assert "\n\n" in posting.description, "Description should have multiple paragraphs"
    assert any(l.startswith("- ") for l in posting.description.splitlines()), "Description should have list items"
    assert any(l.startswith("### ") for l in posting.description.splitlines()), "Description should have headings"
    assert "**" in posting.description, "Description should have bold text"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


def test_source_url_is_human_ad_page(
    adapter: SynprofsAdapter, listing_xml: bytes, detail_html: bytes, monkeypatch
) -> None:
    import re

    import job_scraper.sites.synprofs

    pattern = r"^https://www\.synprofs\.nl/opdracht/[a-z0-9-]+-\d+/$"
    forbidden = ["/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect"]

    monkeypatch.setattr(
        job_scraper.sites.synprofs, "fetch_page", lambda strategy, url: listing_xml
    )
    stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert re.match(pattern, s.detail_url), s.detail_url
        assert not any(f in s.detail_url for f in forbidden)

    stub = next(s for s in stubs if s.listing_id == "6930")
    posting = adapter.parse_detail(stub, detail_html)
    assert posting.source_url == "https://www.synprofs.nl/opdracht/senior-tester-6930/"
    assert re.match(pattern, posting.source_url)
    assert not any(f in posting.source_url for f in forbidden)
    # Matches the detail page's own canonical URL.
    assert f'rel="canonical" href="{posting.source_url}"'.encode() in detail_html


def test_screenshot_selector_matches_description_element(fixtures_dir: Path) -> None:
    from bs4 import BeautifulSoup

    adapter = SynprofsAdapter()
    assert adapter.screenshot_selector
    html = (fixtures_dir / "detail_6930.html").read_text(encoding="utf-8")
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "Inzet van een senior tester die tevens ketentesten kan organiseren en uitvoeren" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()


def test_screenshot_hides_sticky_header(detail_html: bytes) -> None:
    from bs4 import BeautifulSoup

    assert SynprofsAdapter.screenshot_hide_selectors == ("header#masthead",)
    soup = BeautifulSoup(detail_html, "html.parser")
    el = soup.select_one(SynprofsAdapter.screenshot_selector)
    assert el is not None
    for sel in SynprofsAdapter.screenshot_hide_selectors:
        soup.select(sel)  # valid CSS
    assert len(soup.select("header#masthead")) == 1
    assert el.select_one("header#masthead") is None


def test_is_unrelated_redirect_to_listing() -> None:
    from job_scraper.core.gone import is_unrelated_redirect

    adapter = SynprofsAdapter()
    requested = "https://www.synprofs.nl/opdracht/iam-specialist-5927/"
    final = "https://www.synprofs.nl/opdrachten/"
    assert is_unrelated_redirect(
        requested, final, listing_id="5927", listing_paths=adapter.listing_paths
    )


def test_title_has_gone_marker_real_fixture(
    adapter: SynprofsAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.gone import title_has_gone_marker

    result = title_has_gone_marker(detail_html, adapter.gone_markers)
    assert result is None
