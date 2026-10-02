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
