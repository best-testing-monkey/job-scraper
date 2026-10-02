import pytest
from pathlib import Path

from job_scraper.sites.arc_dev import ArcDevAdapter
from job_scraper.core.models import ListingStub
from job_scraper.sites.base import FetchStrategy


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "arc_dev"


@pytest.fixture
def adapter() -> ArcDevAdapter:
    return ArcDevAdapter()


@pytest.fixture
def listing_html(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "listing.html").read_bytes()


@pytest.fixture
def detail_html(fixtures_dir: Path) -> bytes:
    return (fixtures_dir / "detail_pg2lgfgv87.html").read_bytes()


def test_adapter_site_id(adapter: ArcDevAdapter) -> None:
    assert adapter.site_id == "arc_dev"


def test_adapter_base_url(adapter: ArcDevAdapter) -> None:
    assert adapter.base_url == "https://arc.dev"


def test_adapter_fetch_strategy(adapter: ArcDevAdapter) -> None:
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings(adapter: ArcDevAdapter, listing_html: bytes, monkeypatch) -> None:
    def mock_fetch_page(strategy, url):
        return listing_html

    import job_scraper.sites.arc_dev
    monkeypatch.setattr(job_scraper.sites.arc_dev, "fetch_page", mock_fetch_page)

    postings = list(adapter.list_postings())

    assert len(postings) == 1
    assert postings[0].listing_id == "pg2lgfgv87"
    assert isinstance(postings[0], ListingStub)
    assert postings[0].title == "Senior Software Engineer, Test Core"


def test_parse_detail_job_posting(adapter: ArcDevAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="pg2lgfgv87",
        detail_url="/remote-jobs/j/ladders-senior-software-engineer-test-core-pg2lgfgv87",
        title="Senior Software Engineer, Test Core",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "arc_dev"
    assert posting.listing_id == "pg2lgfgv87"
    assert posting.title == "Senior Software Engineer, Test Core"
    assert posting.client == "Ladders"
    assert posting.rate == "N/A"
    assert "Permanent" in posting.duration
    assert len(posting.description) > 0
    assert posting.location == "Remote restrictions apply"
    assert posting.workplace == "Fully Remote"
    assert posting.extra_fields.get("seniority") == "Senior"
    assert posting.extra_fields.get("visa") == "U.S. visa required"


def test_parse_detail_description_markdown(adapter: ArcDevAdapter, detail_html: bytes) -> None:
    stub = ListingStub(
        listing_id="pg2lgfgv87",
        detail_url="/remote-jobs/j/ladders-senior-software-engineer-test-core-pg2lgfgv87",
        title="Senior Software Engineer, Test Core",
    )

    posting = adapter.parse_detail(stub, detail_html)

    # Verify description uses Markdown formatting
    assert "\n\n" in posting.description, "Description should have multiple paragraphs"
    assert any(l.startswith("- ") for l in posting.description.splitlines()), "Description should have list items"
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
    adapter: ArcDevAdapter, listing_html: bytes, detail_html: bytes, monkeypatch
) -> None:
    import re

    import job_scraper.sites.arc_dev

    monkeypatch.setattr(
        job_scraper.sites.arc_dev, "fetch_page", lambda strategy, url: listing_html
    )
    BAD_FRAGMENTS = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")
    pattern = re.compile(r"^https://arc\.dev/remote-jobs/j/[a-z0-9-]+-[a-z0-9]{10}$")

    stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert pattern.match(s.detail_url)
        assert not any(b in s.detail_url for b in BAD_FRAGMENTS)

    posting = adapter.parse_detail(stubs[0], detail_html)
    assert posting.source_url == (
        "https://arc.dev/remote-jobs/j/ladders-senior-software-engineer-test-core-pg2lgfgv87"
    )
    assert pattern.match(posting.source_url)
    assert not any(b in posting.source_url for b in BAD_FRAGMENTS)
