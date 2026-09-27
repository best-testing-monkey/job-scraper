from pathlib import Path
from unittest.mock import patch
from job_scraper.sites.harveynash import HarveyNashAdapter
from job_scraper.sites.base import FetchStrategy
from job_scraper.core.models import ListingStub


def test_harveynash_adapter_attributes():
    adapter = HarveyNashAdapter()
    assert adapter.site_id == "harveynash"
    assert adapter.base_url == "https://www.harveynash.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings():
    adapter = HarveyNashAdapter()
    sitemap_xml = Path("tests/fixtures/harveynash/sitemap.xml").read_text()
    with patch("job_scraper.sites.harveynash.fetch_page", return_value=sitemap_xml):
        postings = list(adapter.list_postings())

    # Should have at least one job posting
    assert len(postings) >= 1

    # Should have the specific job we're testing
    listing_ids = [p.listing_id for p in postings]
    assert "299204" in listing_ids

    # Check the specific job posting
    job_299204 = next((p for p in postings if p.listing_id == "299204"), None)
    assert job_299204 is not None
    assert job_299204.detail_url == "https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert"

    # Should exclude non-job URLs
    all_urls = [p.detail_url for p in postings]
    assert not any("/vacatures/internal" in url for url in all_urls)
    assert not any("/vacatures/thank-you-for-applying" in url for url in all_urls)
    assert not any("/vacatures/thank-you-for-submitting-cv" in url for url in all_urls)


def test_parse_detail():
    adapter = HarveyNashAdapter()
    detail_html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    stub = ListingStub(
        listing_id="299204",
        detail_url="https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert",
        title="Expert (gas)regelvermogen Weert",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "harveynash"
    assert posting.listing_id == "299204"
    assert posting.title == "Expert (gas)regelvermogen Weert"
    assert posting.description != ""
    assert len(posting.description) > 100


def test_parse_detail_full_fields():
    adapter = HarveyNashAdapter()
    detail_html = Path("tests/fixtures/harveynash/detail_299204.html").read_text()
    stub = ListingStub(
        listing_id="299204",
        detail_url="https://www.harveynash.nl/vacatures/299204-Expert-gasregelvermogen-Weert",
        title="Expert (gas)regelvermogen Weert",
    )
    posting = adapter.parse_detail(stub, detail_html)

    assert posting.client == "Enexis"
    assert "Techniek" in posting.category or "Projectbeheersing" in posting.category
    assert posting.location == "Weert, Limburg"
    assert posting.hours == "Fulltime"
    assert posting.rate == "Bespreekbaar"
    assert posting.extra_fields.get("employment_type") == "Interim"
    assert posting.extra_fields.get("expires_at") == "2026-10-02T23:59:59.999Z"
