from pathlib import Path
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
    assert posting.workplace == "Hybrid"
    assert posting.hours == "36 uur"
    assert posting.description
    assert len(posting.description) > 0
    assert posting.posted_date is None
    assert posting.duration is None
    assert posting.scrape_note
    assert "pagination" in posting.scrape_note.lower()
    assert posting.extra_fields.get("contract_type") == "Loondienst (vast)"

    # Verify Markdown conversion
    # The fixture has multiple paragraphs, headings, and lists
    assert "\n\n" in posting.description  # Multiple paragraphs
    assert any(l.startswith("### ") for l in posting.description.splitlines())  # Headings preserved
    assert any(l.startswith("- ") or l.startswith("1. ") for l in posting.description.splitlines())  # List items

    # Verify no lines start with ## (only ### or deeper allowed)
    assert not any(l.startswith("## ") for l in posting.description.splitlines())

    # Verify no trailing whitespace (except for hard breaks which use "  \n")
    for line in posting.description.splitlines():
        if not line.endswith("  "):
            assert line == line.rstrip()


@patch("job_scraper.sites.ictergezocht.fetch_page")
def test_source_url_is_human_ad_page(mock_fetch: object) -> None:
    import re

    pattern = re.compile(r"^https://www\.ictergezocht\.nl/ict-vacature/\d+-[a-z0-9-]+/$")
    bad_parts = ("/apply", "/go/", "/api/", "/wp-json/", ".json", "?utm_", "/redirect")

    with open("tests/fixtures/ictergezocht/detail_438712.html", "rb") as f:
        detail_html = f.read()
    stub = ListingStub(
        listing_id="438712",
        detail_url="https://www.ictergezocht.nl/ict-vacature/438712-senior-functioneel-beheerder-met-rijksoverheid-ervaring/",
        title="Senior Functioneel Beheerder met Rijksoverheid ervaring",
    )
    adapter = IctergezochtAdapter()
    posting = adapter.parse_detail(stub, detail_html)
    assert pattern.match(posting.source_url)
    assert not any(b in posting.source_url for b in bad_parts)

    with open("tests/fixtures/ictergezocht/listing.html", "rb") as f:
        mock_fetch.return_value = f.read()
    stubs = list(adapter.list_postings())
    assert stubs
    for s in stubs:
        assert pattern.match(s.detail_url), s.detail_url
        assert not any(b in s.detail_url for b in bad_parts)


def test_screenshot_selector_matches_description_element() -> None:
    from bs4 import BeautifulSoup

    adapter = IctergezochtAdapter()
    assert adapter.screenshot_selector
    html = Path("tests/fixtures/ictergezocht/detail_438712.html").read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "Wil jij bijdragen aan de rijksoverheid die slimmer, efficiënter" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()
