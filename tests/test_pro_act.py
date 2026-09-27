from pathlib import Path
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
    postings = list(adapter.list_postings(listing_html))
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
    assert posting.rate == "marktconform"
