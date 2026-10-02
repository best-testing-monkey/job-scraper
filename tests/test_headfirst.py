from pathlib import Path
from unittest.mock import patch

from job_scraper.core.models import ListingStub
from job_scraper.sites.base import FetchStrategy
from job_scraper.sites.headfirst import HeadfirstAdapter

FIXTURE_PATH = Path("tests/fixtures/headfirst/listing.html")
TARGET_ID = "28ed2087-a156-462e-b89c-fccc6ff74a71"


def _fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_headfirst_adapter_attributes():
    adapter = HeadfirstAdapter()
    assert adapter.site_id == "headfirst"
    assert adapter.base_url == "https://www.headfirst.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings():
    adapter = HeadfirstAdapter()
    with patch(
        "job_scraper.sites.headfirst.fetch_page", return_value=_fixture_bytes()
    ):
        stubs = list(adapter.list_postings())

    assert len(stubs) >= 5
    for stub in stubs:
        assert stub.detail_url == HeadfirstAdapter.LISTING_URL

    listing_ids = [stub.listing_id for stub in stubs]
    assert TARGET_ID in listing_ids


def test_parse_detail():
    adapter = HeadfirstAdapter()
    stub = ListingStub(
        listing_id=TARGET_ID,
        detail_url=HeadfirstAdapter.LISTING_URL,
        title="Data Engineer (Medior) - RVO",
    )

    posting = adapter.parse_detail(stub, _fixture_bytes())

    assert posting.title == "Data Engineer (Medior) - RVO"
    assert posting.listing_id == TARGET_ID
    assert posting.site_id == "headfirst"
    assert posting.client == "Ministerie van Economische Zaken"
    assert posting.location == "Utrecht"
    assert posting.workplace is None
    assert posting.hours == "32-36"
    assert posting.extra_fields.get("referenceCode") == "SAISAE000050"
    assert posting.description == ""
    assert posting.scrape_note
    assert posting.category is None
    assert posting.rate is None
    assert posting.source_url == HeadfirstAdapter.LISTING_URL


def test_parse_detail_duration_and_apply_url():
    adapter = HeadfirstAdapter()
    stub = ListingStub(
        listing_id=TARGET_ID,
        detail_url=HeadfirstAdapter.LISTING_URL,
        title="Data Engineer (Medior) - RVO",
    )

    posting = adapter.parse_detail(stub, _fixture_bytes())

    assert posting.duration == "2026-10-11 - 2027-04-10"
    assert posting.workplace is None
    assert posting.extra_fields.get("apply_url") == (
        "https://striive.com/nl/opdrachten?id=28ed2087-a156-462e-b89c-fccc6ff74a71"
    )
