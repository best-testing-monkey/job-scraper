import json
from pathlib import Path

import pytest
from unittest.mock import patch

from job_scraper.sites.working_nomads import WorkingNomadsAdapter
from job_scraper.core.models import ListingStub
from job_scraper.sites.base import FetchStrategy


def load_fixture() -> bytes:
    fixture_path = Path(__file__).parent / "fixtures" / "working_nomads" / "listing.json"
    return fixture_path.read_bytes()


def test_adapter_site_id() -> None:
    adapter = WorkingNomadsAdapter()
    assert adapter.site_id == "working_nomads"


def test_adapter_base_url() -> None:
    adapter = WorkingNomadsAdapter()
    assert adapter.base_url == "https://www.workingnomads.com"


def test_adapter_fetch_strategy() -> None:
    adapter = WorkingNomadsAdapter()
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_list_postings_yields_five_stubs() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    assert len(stubs) == 5


def test_list_postings_yields_listing_stubs() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    for stub in stubs:
        assert isinstance(stub, ListingStub)
        assert stub.listing_id
        assert stub.detail_url
        assert stub.title


def test_list_postings_qa_engineer_stub() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())

    qa_stub = stubs[2]
    assert qa_stub.listing_id == "1843242"
    assert qa_stub.title == "Senior QA Automation Engineer"
    assert qa_stub.detail_url == "https://www.workingnomads.com/job/go/1843242/"


def test_parse_detail_returns_correct_site_id() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.site_id == "working_nomads"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_correct_listing_id() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.listing_id == "1843242"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_correct_title() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.title == "Senior QA Automation Engineer"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_correct_client() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.client == "Proxify"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_correct_location() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.location == "Time zone: CET (+/- 3 hours)"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_qa_tags_in_category() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert "qa" in posting.category.lower()
    assert "playwright" in posting.category.lower()
    assert "selenium" in posting.category.lower()
    assert "test automation" in posting.category.lower()
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_non_empty_description() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.description
    assert len(posting.description) > 0
    assert "Senior QA Automation Engineer" in posting.description or "Proxify" in posting.description
    assert posting.workplace == "Fully Remote"


def test_parse_detail_returns_correct_posted_date() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.posted_date == "2026-09-07T14:40:19-04:00"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_hours_is_none() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.hours is None
    assert posting.workplace == "Fully Remote"


def test_parse_detail_rate_is_none() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.rate is None
    assert posting.workplace == "Fully Remote"


def test_parse_detail_duration_is_none() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.duration is None
    assert posting.workplace == "Fully Remote"


def test_parse_detail_stores_category_name_in_extra_fields() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)
    assert posting.extra_fields.get("category_name") == "Development"
    assert posting.workplace == "Fully Remote"


def test_parse_detail_ignores_page_argument() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting1 = adapter.parse_detail(stubs[2], b"ignored page 1")
    posting2 = adapter.parse_detail(stubs[2], b"ignored page 2")
    assert posting1.title == posting2.title
    assert posting1.client == posting2.client


def test_parse_detail_description_markdown() -> None:
    adapter = WorkingNomadsAdapter()
    fixture = load_fixture()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=fixture):
        stubs = list(adapter.list_postings())
    posting = adapter.parse_detail(stubs[2], None)

    # Verify no ## headings (only ### and deeper)
    assert not any(l.startswith("## ") for l in posting.description.splitlines()), "Description should not have ## headings"

    # Verify no trailing whitespace except for hard breaks
    for line in posting.description.splitlines():
        if not line.endswith("  "):  # Allow hard breaks (two spaces)
            assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"

    # Verify non-empty
    assert posting.description.strip(), "Description should not be empty"


BASE = "https://www.workingnomads.com/jobs/"
KNOWN = [
    ("1785901", "Face Deduplication Collection", "TELUS Digital", "face-deduplication-collection-telus-digital"),
    ("1850911", "Senior Google Ads Account Manager - Remote (Work From Home)", "StubGroup", "senior-google-ads-account-manager-remote-work-from-home-stubgroup-1850911"),
    ("1889808", "Stack .NET Developer / Algorithm Engineer \u2013 Backend Focus.", "CloudGeometry", "stack-net-developer-algorithm-engineer-backend-focus-cloudgeometry-1889808"),
    ("1891955", "Beekman Social - Account Manager", "Beekman Social", "beekman-social-account-manager-beekman-social"),
]
INDEX_PAGE = b'<html><head><link rel="canonical" href="https://www.workingnomads.com/jobs"></head></html>'


def canonical_page(url: str) -> bytes:
    return f'<html><head><link rel="canonical" href="{url}"></head></html>'.encode()


def make_stub(listing_id: str, title: str) -> ListingStub:
    return ListingStub(
        listing_id=listing_id,
        detail_url=f"https://www.workingnomads.com/job/go/{listing_id}/",
        title=title,
    )


def test_candidates_contain_real_slug() -> None:
    from job_scraper.core.markdown_export import slugify

    for listing_id, title, company, slug in KNOWN:
        base = f"{slugify(title)}-{slugify(company)}"
        assert slug in (base, f"{base}-{listing_id}")


def test_parse_detail_canonical_from_page_wins() -> None:
    adapter = WorkingNomadsAdapter()
    adapter._job_cache["1785901"] = {"title": "Face Deduplication Collection", "company_name": "TELUS Digital"}
    page = (Path(__file__).parent / "fixtures" / "working_nomads" / "detail_1785901.html").read_bytes()
    with patch("job_scraper.sites.working_nomads.fetch_page", side_effect=AssertionError("no fetch")):
        posting = adapter.parse_detail(make_stub("1785901", "x"), page)
    assert posting.source_url == BASE + "face-deduplication-collection-telus-digital"


@pytest.mark.parametrize("listing_id,title,company,slug", KNOWN)
def test_resolve_known_triples(listing_id: str, title: str, company: str, slug: str) -> None:
    adapter = WorkingNomadsAdapter()
    adapter._job_cache[listing_id] = {"title": title, "company_name": company}

    def fake(strategy: FetchStrategy, url: str) -> bytes:
        return canonical_page(url) if url == BASE + slug else INDEX_PAGE

    with patch("job_scraper.sites.working_nomads.fetch_page", side_effect=fake):
        posting = adapter.parse_detail(make_stub(listing_id, title), None)
    assert posting.source_url == BASE + slug


def test_resolve_bare_slug_valid() -> None:
    adapter = WorkingNomadsAdapter()
    with patch("job_scraper.sites.working_nomads.fetch_page", side_effect=lambda s, u: canonical_page(u + "/")) as m:
        url = adapter._resolve_human_url("a-b", "7")
    assert url == BASE + "a-b"
    assert m.call_count == 1


def test_resolve_suffixed_when_bare_redirects() -> None:
    adapter = WorkingNomadsAdapter()
    pages = {BASE + "a-b": INDEX_PAGE, BASE + "a-b-7": canonical_page(BASE + "a-b-7")}
    with patch("job_scraper.sites.working_nomads.fetch_page", side_effect=lambda s, u: pages[u]):
        assert adapter._resolve_human_url("a-b", "7") == BASE + "a-b-7"


def test_resolve_both_invalid_falls_back(capsys: pytest.CaptureFixture[str]) -> None:
    adapter = WorkingNomadsAdapter()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=INDEX_PAGE):
        assert adapter._resolve_human_url("a-b", "7") == BASE + "a-b-7"
    assert "working_nomads: could not verify human URL for 7" in capsys.readouterr().err


def test_resolve_fetch_error_falls_back(capsys: pytest.CaptureFixture[str]) -> None:
    adapter = WorkingNomadsAdapter()
    with patch("job_scraper.sites.working_nomads.fetch_page", side_effect=RuntimeError("boom")):
        assert adapter._resolve_human_url("a-b", "7") == BASE + "a-b-7"
    assert "could not verify human URL for 7" in capsys.readouterr().err


def test_all_listing_jobs_have_human_source_url() -> None:
    adapter = WorkingNomadsAdapter()
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=load_fixture()):
        stubs = list(adapter.list_postings())
    with patch("job_scraper.sites.working_nomads.fetch_page", return_value=INDEX_PAGE):
        postings = [adapter.parse_detail(stub, None) for stub in stubs]
    assert len(postings) == len(json.loads(load_fixture()))
    for posting in postings:
        assert posting.source_url.startswith(BASE)
        assert "/job/go/" not in posting.source_url
        assert "/api/" not in posting.source_url


@pytest.mark.parametrize(
    "fixture",
    ["detail_1785901.html"],
)
def test_screenshot_selector_matches_description_element(fixture: str) -> None:
    from bs4 import BeautifulSoup

    adapter = WorkingNomadsAdapter()
    assert adapter.screenshot_selector
    html = (Path(__file__).parent / "fixtures" / "working_nomads" / fixture).read_text()
    els = BeautifulSoup(html, "html.parser").select(adapter.screenshot_selector)
    assert len(els) == 1
    assert "The objective of this project is to collect a large and diverse dataset" in els[0].get_text()
    assert els[0].find(["nav", "header", "footer", "form"]) is None
    assert "cookie" not in els[0].get_text().lower()
