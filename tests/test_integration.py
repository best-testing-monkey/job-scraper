from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch, MagicMock
import tempfile
import re

import pytest

from job_scraper.core.db import JobRepository
from job_scraper.core.models import ListingStub, JobPosting
from job_scraper.pipeline import run
from job_scraper.sites.pro_act import ProActAdapter
from job_scraper.sites.hero import HeroAdapter
from job_scraper.sites.flexvalue import FlexValueAdapter
from job_scraper.sites.synprofs import SynprofsAdapter
from job_scraper.sites.stone_interim import StoneInterimAdapter
from job_scraper.sites.tender_link import TenderLinkAdapter
from job_scraper.sites.harveynash import HarveyNashAdapter
from job_scraper.sites.headfirst import HeadfirstAdapter
from job_scraper.sites.sevenstars import SevenstarsAdapter
from job_scraper.sites.circle8 import Circle8Adapter
from job_scraper.sites.base import SiteAdapter


def load_fixture(site_id: str, filename: str) -> str:
    """Load HTML fixture from tests/fixtures/<site_id>/<filename>."""
    fixture_path = Path(__file__).parent / "fixtures" / site_id / filename
    return fixture_path.read_text(encoding="utf-8")


def load_fixture_bytes(site_id: str, filename: str) -> bytes:
    """Load a fixture's raw bytes from tests/fixtures/<site_id>/<filename>."""
    fixture_path = Path(__file__).parent / "fixtures" / site_id / filename
    return fixture_path.read_bytes()


class FixtureAwareProActAdapter(ProActAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "8887":  # We have detail_8887.html
                yield stub

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        posting = super().parse_detail(stub, page)
        # Clean up description by removing form field labels that appear in the fixture
        # The fixture mixes actual job description with form option labels
        description = posting.description
        # Keep only the main content before form fields start (marked by form field labels)
        # Extract the content from "Opdrachtomschrijving" to "Interesse?" which is the actual job content
        match = re.search(r"Opdrachtomschrijving(.*?)Interesse\?", description, re.DOTALL)
        if match:
            description = "Opdrachtomschrijving" + match.group(1)
        description = re.sub(r"\s+", " ", description).strip()
        posting.description = description
        return posting


class FixtureAwareHeroAdapter(HeroAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "e98187b8":  # We have detail_e98187b8.html
                yield stub


class FixtureAwareFlexValueAdapter(FlexValueAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "1065407":  # We have detail_1065407.html
                yield stub


class FixtureAwareSynprofsAdapter(SynprofsAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "6930":  # We have detail_6930.html
                yield stub

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        posting = super().parse_detail(stub, page)
        # The fixture's description carries a "not suitable for zzp" boilerplate
        # disclaimer that matches an EXCLUSION_KEYWORDS entry; strip it so the
        # fixture exercises the same happy path as the other sites' fixtures.
        description = re.sub(
            r"Deze functie is niet geschikt voor zzp.*?geen eigenaar van zijn\.",
            "",
            posting.description,
        )
        posting.description = re.sub(r"\s+", " ", description).strip()
        return posting


class FixtureAwareStoneInterimAdapter(StoneInterimAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "4893":  # We have detail_4893_api_GetVacancy.json
                yield stub


class FixtureAwareTenderLinkAdapter(TenderLinkAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "33345":  # cached record already has full detail
                yield stub


class FixtureAwareHarveyNashAdapter(HarveyNashAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "299204":  # We have detail_299204.html
                yield stub


class FixtureAwareHeadfirstAdapter(HeadfirstAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "28ed2087-a156-462e-b89c-fccc6ff74a71":
                yield stub


class FixtureAwareSevenstarsAdapter(SevenstarsAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "7S-004982":  # We have detail_7S-004982.html
                yield stub


class FixtureAwareCircle8Adapter(Circle8Adapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "VNR-85422":  # We have detail_VNR-85422.html
                yield stub


@pytest.fixture
def fixture_fetch_page():
    """Create a monkeypatch function for fetch_page that returns fixture HTML
    for both listing-page and detail-page URLs."""

    def mock_fetch_page(strategy: Any, url: str) -> Any:
        if url == ProActAdapter.LISTING_URL:
            return load_fixture("pro_act", "listing.html")
        if url == HeroAdapter.LISTING_URL:
            return load_fixture("hero", "listing.html")
        if url == FlexValueAdapter.LISTING_URL:
            return load_fixture("flexvalue", "listing.html")
        if url == SynprofsAdapter.LISTING_URL:
            return load_fixture_bytes("synprofs", "listing.xml")
        if url == TenderLinkAdapter.LISTING_URL:
            return load_fixture_bytes("tender_link", "listing.json")
        if url == HarveyNashAdapter.LISTING_URL:
            return load_fixture_bytes("harveynash", "sitemap.xml")
        if url == HeadfirstAdapter.LISTING_URL:
            return load_fixture_bytes("headfirst", "listing.html")
        if url == SevenstarsAdapter.LISTING_URL:
            return load_fixture_bytes("sevenstars", "listing.html")
        if url == Circle8Adapter.LISTING_URL:
            return load_fixture_bytes("circle8", "listing.html")
        if "pro-act.nl" in url and "8887" in url:
            return load_fixture("pro_act", "detail_8887.html")
        elif "hero.eu" in url and "e98187b8" in url:
            return load_fixture("hero", "detail_e98187b8.html")
        elif "flexvalue" in url and "1065407" in url:
            return load_fixture("flexvalue", "detail_1065407.html")
        elif "synprofs.nl" in url and "6930" in url:
            return load_fixture_bytes("synprofs", "detail_6930.html")
        elif "stone-interim.nl" in url and "4893" in url:
            return load_fixture_bytes("stone_interim", "detail_4893_api_GetVacancy.json")
        elif "harveynash.nl" in url and "299204" in url:
            return load_fixture_bytes("harveynash", "detail_299204.html")
        elif "sevenstars.nl" in url and "7S-004982" in url:
            return load_fixture_bytes("sevenstars", "detail_7S-004982.html")
        elif "circle8.nl" in url and "VNR-85422" in url:
            return load_fixture_bytes("circle8", "detail_VNR-85422.html")
        # Return empty HTML for URLs we don't have fixtures for
        return "<html></html>"

    return mock_fetch_page


ALL_SITE_IDS = [
    "pro_act",
    "hero",
    "flexvalue",
    "synprofs",
    "stone_interim",
    "tender_link",
    "harveynash",
    "headfirst",
    "sevenstars",
    "circle8",
]


def test_integration_end_to_end(tmp_path: Path, fixture_fetch_page: Any) -> None:
    """End-to-end integration test: scrape all 10 sites, verify output and idempotence."""
    db_path = tmp_path / "scraper.db"
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    repo = JobRepository(str(db_path))

    # First run: scrape all sites from fixtures
    fake_registry = {
        "pro_act": FixtureAwareProActAdapter,
        "hero": FixtureAwareHeroAdapter,
        "flexvalue": FixtureAwareFlexValueAdapter,
        "synprofs": FixtureAwareSynprofsAdapter,
        "stone_interim": FixtureAwareStoneInterimAdapter,
        "tender_link": FixtureAwareTenderLinkAdapter,
        "harveynash": FixtureAwareHarveyNashAdapter,
        "headfirst": FixtureAwareHeadfirstAdapter,
        "sevenstars": FixtureAwareSevenstarsAdapter,
        "circle8": FixtureAwareCircle8Adapter,
    }

    stone_interim_response = MagicMock()
    stone_interim_response.body = load_fixture_bytes(
        "stone_interim", "listing_api_GetOverviewItems.json"
    )

    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry), \
         patch("job_scraper.pipeline.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.pro_act.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.hero.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.flexvalue.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.synprofs.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.tender_link.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.harveynash.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.headfirst.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.sevenstars.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.circle8.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.stone_interim.Fetcher.post", return_value=stone_interim_response):
        # ignore_robots=True: stone-interim.nl's WAF returns 403 to urllib's
        # default user agent when fetching robots.txt itself (unrelated to the
        # adapter's own fetch mechanics, which use scrapling and succeed fine),
        # which Python's robotparser treats as disallow-all. This test cares
        # about adapter/pipeline behavior against fixtures, not live robots.txt
        # fetch results for 10 real domains.
        results_first = run(ALL_SITE_IDS, repo, str(jobs_dir), ignore_robots=True)

    # Assertions for first run
    for site_id in ALL_SITE_IDS:
        assert site_id in results_first

        # Each site should have at least 1 posting written and seen
        assert results_first[site_id]["written"] >= 1, (
            f"{site_id} should write at least 1 posting, got {results_first[site_id]}"
        )
        assert results_first[site_id]["seen"] >= 1

        # Check that a markdown file was created for at least one posting
        site_files = list(jobs_dir.glob(f"{site_id}-*.md"))
        assert len(site_files) >= 1, (
            f"Expected at least 1 {site_id} markdown file, found {len(site_files)}"
        )
        assert any(f.exists() for f in site_files), f"{site_id} markdown files should exist"

    # Second run: run again with same fixtures, verify idempotence
    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry), \
         patch("job_scraper.pipeline.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.pro_act.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.hero.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.flexvalue.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.synprofs.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.tender_link.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.harveynash.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.headfirst.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.sevenstars.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.circle8.fetch_page", side_effect=fixture_fetch_page), \
         patch("job_scraper.sites.stone_interim.Fetcher.post", return_value=stone_interim_response):
        results_second = run(ALL_SITE_IDS, repo, str(jobs_dir), ignore_robots=True)

    # On the second run, nothing should change (idempotence)
    for site_id in ALL_SITE_IDS:
        assert results_second[site_id]["written"] == 0, (
            f"Second run should not write any new {site_id} postings, got {results_second[site_id]}"
        )
        assert results_second[site_id]["seen"] == results_first[site_id]["seen"]
