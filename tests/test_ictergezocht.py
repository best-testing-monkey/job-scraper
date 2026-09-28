from unittest.mock import patch

from job_scraper.core.models import ListingStub
from job_scraper.sites.ictergezocht import IctergezochtAdapter


@patch("job_scraper.sites.ictergezocht.fetch_page")
def test_list_postings(mock_fetch: object) -> None:
    with open("tests/fixtures/ictergezocht/listing.html", "rb") as f:
        listing_html = f.read()
    mock_fetch.return_value = listing_html

    adapter = IctergezochtAdapter()
    stubs = list(adapter.list_postings())

    assert len(stubs) > 0
    assert any(stub.listing_id == "438712" for stub in stubs)

    stub_438712 = next(stub for stub in stubs if stub.listing_id == "438712")
    assert stub_438712.title == "Senior Functioneel Beheerder met Rijksoverheid ervaring"
    assert (
        stub_438712.detail_url
        == "https://www.ictergezocht.nl/ict-vacature/438712-senior-functioneel-beheerder-met-rijksoverheid-ervaring/"
    )


@patch("job_scraper.sites.ictergezocht.fetch_page")
def test_parse_detail(mock_fetch: object) -> None:
    with open("tests/fixtures/ictergezocht/detail_438712.html", "rb") as f:
        detail_html = f.read()
    mock_fetch.return_value = detail_html

    adapter = IctergezochtAdapter()
    stub = ListingStub(
        listing_id="438712",
        detail_url="https://www.ictergezocht.nl/ict-vacature/438712-senior-functioneel-beheerder-met-rijksoverheid-ervaring/",
        title="Senior Functioneel Beheerder met Rijksoverheid ervaring",
    )

    posting = adapter.parse_detail(stub, detail_html)

    assert posting.site_id == "ictergezocht"
    assert posting.listing_id == "438712"
    assert "Functioneel Beheerder" in posting.title
    assert posting.client == "Concretor"
    assert posting.location == "Barendrecht"
    assert posting.hours == "36 uur"
    assert posting.description
    assert len(posting.description) > 0
    assert posting.posted_date is None
    assert posting.duration is None
    assert posting.scrape_note
    assert "pagination" in posting.scrape_note.lower()
    assert posting.extra_fields.get("contract_type") == "Loondienst (vast)"
