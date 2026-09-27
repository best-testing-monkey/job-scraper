from pathlib import Path

from job_scraper.sites.flexvalue import FlexValueAdapter
from job_scraper.sites.base import FetchStrategy


def load_fixture(filename: str) -> str:
    fixture_path = Path(__file__).parent / "fixtures" / "flexvalue" / filename
    return fixture_path.read_text()


def test_adapter_properties() -> None:
    adapter = FlexValueAdapter()
    assert adapter.site_id == "flexvalue"
    assert adapter.base_url == "https://aanvragen.flexvalue.nl"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings() -> None:
    listing_html = load_fixture("listing.html")
    adapter = FlexValueAdapter()
    adapter.page = listing_html

    postings = list(adapter.list_postings())

    assert len(postings) > 0

    found_1065407 = False
    for posting in postings:
        assert posting.listing_id
        assert posting.detail_url
        assert posting.detail_url.startswith("https://aanvragen.flexvalue.nl")
        assert posting.title

        if posting.listing_id == "1065407":
            found_1065407 = True
            assert posting.title == "Java Devops Engineer"

    assert found_1065407, "Should find listing with id 1065407"


def test_parse_detail() -> None:
    detail_html = load_fixture("detail_1065407.html")
    adapter = FlexValueAdapter()

    from job_scraper.core.models import ListingStub
    stub = ListingStub(
        listing_id="1065407",
        detail_url="https://aanvragen.flexvalue.nl/careers/6605/jobs/1065407-Java-Devops-Engineer",
        title="Java Devops Engineer",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.title == "Java Devops Engineer"
    assert posting.listing_id == "1065407"
    assert posting.site_id == "flexvalue"
    assert posting.location == "Apeldoorn, Gelderland"
    assert posting.hours == "36"
    assert posting.duration is not None
    assert "12-10-2026" in posting.duration
    assert "31-12-2026" in posting.duration
    assert posting.extra_fields.get("Optie op verlenging") == "Ja"
    assert posting.description
    assert len(posting.description) > 0
    assert posting.client == "Belastingdienst"
    assert posting.category is None
    assert posting.rate is None
