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
    assert "2026-09-26" in posting.posted_date
    assert posting.rate is None
    assert posting.duration is None
    assert len(posting.description) > 2000
    assert "Digis" in posting.description
    assert posting.extra_fields.get("validThrough") is not None
    assert posting.extra_fields.get("employmentType") == "FULL_TIME"
