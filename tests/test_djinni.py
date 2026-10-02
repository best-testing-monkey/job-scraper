import pytest
from pathlib import Path

from job_scraper.sites.djinni import DjinniAdapter
from job_scraper.core.models import ListingStub
from job_scraper.sites.base import FetchStrategy


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "djinni"


@pytest.fixture
def adapter() -> DjinniAdapter:
    return DjinniAdapter()


@pytest.fixture
def listing_html(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "listing.html").read_bytes()


@pytest.fixture
def detail_html(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "detail_848723.html").read_bytes()


def test_adapter_site_id(adapter: DjinniAdapter) -> None:
    assert adapter.site_id == "djinni"


def test_adapter_base_url(adapter: DjinniAdapter) -> None:
    assert adapter.base_url == "https://djinni.co"


def test_adapter_fetch_strategy(adapter: DjinniAdapter) -> None:
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings(adapter: DjinniAdapter, listing_html: bytes, monkeypatch) -> None:
    def mock_fetch_page(strategy, url):
        return listing_html

    import job_scraper.sites.djinni
    monkeypatch.setattr(job_scraper.sites.djinni, "fetch_page", mock_fetch_page)

    postings = list(adapter.list_postings())

    assert len(postings) > 0
    assert any(p.listing_id == "848723" for p in postings)

    target_stub = next(p for p in postings if p.listing_id == "848723")
    assert isinstance(target_stub, ListingStub)
    assert target_stub.listing_id == "848723"
    assert "848723" in target_stub.detail_url
    assert target_stub.title == "Senior Manual QA Engineer - Warsaw (On-site)"


def test_parse_detail_job_posting(adapter: DjinniAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="848723",
        detail_url="https://djinni.co/jobs/848723-senior-manual-qa-engineer-warsaw-on-site/",
        title="Senior Manual QA Engineer - Warsaw (On-site)",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "djinni"
    assert posting.listing_id == "848723"
    assert posting.title == "Senior Manual QA Engineer - Warsaw (On-site)"
    assert "Digis" in posting.client
    assert posting.category == "QA"
    assert "Poland" in posting.location
    assert posting.workplace == "On-site"
    assert "2026-09-26" in posting.posted_date
    assert posting.rate is None
    assert posting.duration is None
    assert len(posting.description) > 2000
    assert "Digis" in posting.description
    assert posting.extra_fields.get("validThrough") is not None
    assert posting.extra_fields.get("employmentType") == "FULL_TIME"


def test_parse_detail_description_markdown(adapter: DjinniAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="848723",
        detail_url="https://djinni.co/jobs/848723-senior-manual-qa-engineer-warsaw-on-site/",
        title="Senior Manual QA Engineer - Warsaw (On-site)",
    )

    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses Markdown formatting (hard breaks from \n)
    assert "\n\n" in posting.description, "Description should have multiple paragraphs separated by blank lines"

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


def test_parse_detail_workplace_options_list(
    adapter: DjinniAdapter, fixtures_dir: Path
) -> None:
    """djinni pages carry a details-list entry ("Office, Remote, Hybrid
    Remote") listing every arrangement the employer accepts for this
    posting, separate from the JSON-LD block and from any title suffix.
    Location alone ("Ukraine") and the title alone give no signal here —
    this fixture only classifies correctly because of that details-list
    entry, which lists "Remote" as one of the accepted options."""
    detail_html = (fixtures_dir / "detail_850338.html").read_bytes()
    stub = ListingStub(
        listing_id="850338",
        detail_url="https://djinni.co/jobs/850338-strong-junior-middle-general-qa-engineer/",
        title="Strong Junior\\Middle General QA Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.location == "Ukraine"
    assert posting.workplace == "Fully Remote"


def test_source_url_is_human_ad_page(
    adapter: DjinniAdapter, listing_html: bytes, detail_html: bytes, monkeypatch
) -> None:
    import re

    import job_scraper.sites.djinni

    # Single listing page: stop pagination by serving the same page once.
    calls = {"n": 0}

    def mock_fetch_page(strategy, url):
        calls["n"] += 1
        return listing_html

    monkeypatch.setattr(job_scraper.sites.djinni, "fetch_page", mock_fetch_page)
    BAD_FRAGMENTS = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    pattern = re.compile(r"^https://djinni\.co/jobs/\d+-[a-z0-9-]+/$")

    stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert pattern.match(s.detail_url), s.detail_url
        assert not any(b in s.detail_url for b in BAD_FRAGMENTS)

    stub = next(s for s in stubs if s.listing_id == "848723")
    posting = adapter.parse_detail(stub, detail_html)
    assert posting.source_url == (
        "https://djinni.co/jobs/848723-senior-manual-qa-engineer-warsaw-on-site/"
    )
    assert pattern.match(posting.source_url)
    assert not any(b in posting.source_url for b in BAD_FRAGMENTS)
