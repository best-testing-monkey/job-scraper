import pytest
from unittest.mock import patch

from job_scraper.sites.wearedevelopers import WearedevelopersAdapter


@pytest.fixture
def adapter() -> WearedevelopersAdapter:
    return WearedevelopersAdapter()


@pytest.fixture
def listing_html() -> bytes:
    with open("tests/fixtures/wearedevelopers/listing.html", "rb") as f:
        return f.read()


@pytest.fixture
def detail_html() -> bytes:
    with open("tests/fixtures/wearedevelopers/detail_2904764.html", "rb") as f:
        return f.read()


def test_list_postings(adapter: WearedevelopersAdapter, listing_html: bytes) -> None:
    with patch("job_scraper.sites.wearedevelopers.fetch_page", return_value=listing_html):
        stubs = list(adapter.list_postings())

        assert len(stubs) > 0
        assert len(stubs) == 24

        ids = [stub.listing_id for stub in stubs]
        assert "2904764" in ids

        stub_2904764 = next(s for s in stubs if s.listing_id == "2904764")
        assert stub_2904764.title
        assert "/jobs/ext/2904764" in stub_2904764.detail_url


def test_parse_detail_basic(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "wearedevelopers"
    assert posting.listing_id == "2904764"
    assert posting.title == "Senior Qa Testing Engineer"
    assert posting.client == "AILY LABS"
    assert posting.location == "Barcelona, Spain"
    assert posting.posted_date == "2026-09-14"
    assert posting.rate is None
    assert posting.hours is None
    assert posting.duration is None


def test_parse_detail_description(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.description
    assert len(posting.description) > 0
    assert "Mission" in posting.description or "QA" in posting.description

    # Verify Markdown conversion
    # Verify no lines start with ## (only ### or deeper allowed)
    assert not any(l.startswith("## ") for l in posting.description.splitlines())

    # Verify no trailing whitespace (except for hard breaks which use "  \n")
    for line in posting.description.splitlines():
        if not line.endswith("  "):
            assert line == line.rstrip()


def test_parse_detail_scrape_note(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.scrape_note
    assert "pagination" in posting.scrape_note.lower()
    assert "Hotwire" in posting.scrape_note or "Turbo" in posting.scrape_note


def test_parse_detail_category(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.category
    assert "Testing" in posting.category or "JavaScript" in posting.category


def test_parse_detail_workplace_badge_remote(
    adapter: WearedevelopersAdapter, detail_html: bytes
) -> None:
    from job_scraper.core.models import ListingStub

    stub = ListingStub(
        listing_id="2904764",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2904764-senior-qa-testing-engineer",
        title="Senior Qa Testing Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    # This posting anchors on a city (Barcelona) but the page also carries
    # a "Remote" badge — the badge is the authoritative signal, so the job
    # is still classified Fully Remote despite the city in Location.
    assert posting.location == "Barcelona, Spain"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_workplace_no_badge(adapter: WearedevelopersAdapter) -> None:
    from job_scraper.core.models import ListingStub

    with open("tests/fixtures/wearedevelopers/detail_2203015.html", "rb") as f:
        page = f.read()

    stub = ListingStub(
        listing_id="2203015",
        detail_url="https://www.wearedevelopers.com/jobs/ext/2203015-x",
        title="Qa / Qa Automation - Sap",
    )

    posting = adapter.parse_detail(stub, page)

    assert posting.location == "Pontevedra, Spain"
    assert posting.workplace is None


def test_parse_detail_workplace_badge_us(adapter: WearedevelopersAdapter) -> None:
    from job_scraper.core.models import ListingStub

    with open("tests/fixtures/wearedevelopers/detail_1343363.html", "rb") as f:
        page = f.read()

    stub = ListingStub(
        listing_id="1343363",
        detail_url="https://www.wearedevelopers.com/jobs/ext/1343363-x",
        title="QA Engineer (Manual / Automation)",
    )

    posting = adapter.parse_detail(stub, page)

    assert posting.location == "United States"
    assert posting.workplace == "Fully Remote"


def test_adapter_constants(adapter: WearedevelopersAdapter) -> None:
    assert adapter.site_id == "wearedevelopers"
    assert adapter.base_url == "https://www.wearedevelopers.com"
    assert adapter.fetch_strategy.value == "stealth"
