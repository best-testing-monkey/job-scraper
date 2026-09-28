from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch, MagicMock
import contextlib
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
from job_scraper.sites.iamexpat import IamexpatAdapter
from job_scraper.sites.djinni import DjinniAdapter
from job_scraper.sites.arc_dev import ArcDevAdapter
from job_scraper.sites.freelancer_com import FreelancerComAdapter
from job_scraper.sites.guru import GuruAdapter
from job_scraper.sites.planet_interim import PlanetInterimAdapter
from job_scraper.sites.ictergezocht import IctergezochtAdapter
from job_scraper.sites.wearedevelopers import WearedevelopersAdapter
from job_scraper.sites.working_nomads import WorkingNomadsAdapter
from job_scraper.sites.freelancermap import FreelancermapAdapter
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


class FixtureAwareIamexpatAdapter(IamexpatAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "tLJWUBCWY1P8MBXMScbwRE":  # We have detail_tLJWUBCWY1P8MBXMScbwRE.html
                yield stub


class FixtureAwareDjinniAdapter(DjinniAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "848723":  # We have detail_848723.html
                yield stub


class FixtureAwareFreelancerComAdapter(FreelancerComAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "astrology-app-tester-required":  # We have detail_40724221.html
                yield stub


class FixtureAwareGuruAdapter(GuruAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            # "2120954" is the only job actually present in listing.html.
            # Our only saved guru detail fixture (detail_2101732.html) was
            # captured from a different, separately-scraped posting — there's
            # no overlap between the two fixtures' ids. We filter down to the
            # real listing's job here and pair it with that detail fixture in
            # fixture_fetch_page below; parse_detail takes listing_id from the
            # stub, not from the HTML, so this is safe for exercising the
            # pipeline end-to-end.
            if stub.listing_id == "2120954":
                yield stub


class FixtureAwarePlanetInterimAdapter(PlanetInterimAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "539572":  # We have detail_539572.html
                yield stub


class FixtureAwareIctergezochtAdapter(IctergezochtAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "438712":  # We have detail_438712.html
                yield stub


class FixtureAwareWearedevelopersAdapter(WearedevelopersAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "2904764":  # We have detail_2904764.html
                yield stub


class FixtureAwareWorkingNomadsAdapter(WorkingNomadsAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "1843242":  # cached record already has full detail
                yield stub


class FixtureAwareFreelancermapAdapter(FreelancermapAdapter):
    """Wrapper adapter that filters list_postings down to fixture-backed listings."""

    def list_postings(self) -> Iterator[ListingStub]:
        for stub in super().list_postings():
            if stub.listing_id == "3051456":  # We have detail_test-automation-consultant-m-w-d-playwright.html
                yield stub


@pytest.fixture
def fixture_fetch_page():
    """Create a monkeypatch function for fetch_page that returns fixture HTML
    for both listing-page and detail-page URLs."""

    def mock_fetch_page(strategy: Any, url: str, **kwargs: Any) -> Any:
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
        if url == f"{IamexpatAdapter.LISTING_URL}?page=1":
            return load_fixture_bytes("iamexpat", "listing.html")
        if url == DjinniAdapter.LISTING_URL:
            return load_fixture_bytes("djinni", "listing.html")
        if url == ArcDevAdapter.LISTING_URL:
            return load_fixture_bytes("arc_dev", "listing.html")
        if url == FreelancerComAdapter.LISTING_URL:
            return load_fixture_bytes("freelancer_com", "listing.html")
        if url == GuruAdapter.LISTING_URL:
            return load_fixture_bytes("guru", "listing.html")
        if url == PlanetInterimAdapter.LISTING_URL:
            return load_fixture_bytes("planet_interim", "listing.html")
        if url == IctergezochtAdapter.LISTING_URL:
            return load_fixture_bytes("ictergezocht", "listing.html")
        if url == WearedevelopersAdapter.LISTING_URL:
            return load_fixture_bytes("wearedevelopers", "listing.html")
        if url == WorkingNomadsAdapter.LISTING_URL:
            return load_fixture_bytes("working_nomads", "listing.json")
        if url == FreelancermapAdapter.LISTING_URL:
            return load_fixture_bytes("freelancermap", "listing.html")
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
        elif "iamexpat.nl" in url and "tLJWUBCWY1P8MBXMScbwRE" in url:
            return load_fixture_bytes("iamexpat", "detail_tLJWUBCWY1P8MBXMScbwRE.html")
        elif "djinni.co" in url and "848723" in url:
            return load_fixture_bytes("djinni", "detail_848723.html")
        elif "pg2lgfgv87" in url:
            return load_fixture_bytes("arc_dev", "detail_pg2lgfgv87.html")
        elif "freelancer.com" in url and "astrology-app-tester-required" in url:
            return load_fixture_bytes("freelancer_com", "detail_40724221.html")
        elif "guru.com" in url and "2120954" in url:
            return load_fixture_bytes("guru", "detail_2101732.html")
        elif "planetinterim.nl" in url and "539572" in url:
            return load_fixture_bytes("planet_interim", "detail_539572.html")
        elif "ictergezocht.nl" in url and "438712" in url:
            return load_fixture_bytes("ictergezocht", "detail_438712.html")
        elif "wearedevelopers.com" in url and "2904764" in url:
            return load_fixture_bytes("wearedevelopers", "detail_2904764.html")
        elif "freelancermap.de" in url and "test-automation-consultant-m-w-d-playwright" in url:
            return load_fixture_bytes(
                "freelancermap", "detail_test-automation-consultant-m-w-d-playwright.html"
            )
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
    "iamexpat",
    "djinni",
    "arc_dev",
    "freelancer_com",
    "guru",
    "planet_interim",
    "ictergezocht",
    "wearedevelopers",
    "working_nomads",
    "freelancermap",
]


_ALL_SITE_MODULES = (
    "pro_act",
    "hero",
    "flexvalue",
    "synprofs",
    "tender_link",
    "harveynash",
    "headfirst",
    "sevenstars",
    "circle8",
    "iamexpat",
    "djinni",
    "arc_dev",
    "freelancer_com",
    "guru",
    "planet_interim",
    "ictergezocht",
    "wearedevelopers",
    "working_nomads",
    "freelancermap",
)


def _patch_all_sites(
    stack: contextlib.ExitStack,
    fake_registry: dict[str, Any],
    fixture_fetch_page: Any,
    stone_interim_response: MagicMock,
) -> None:
    """Enter every fixture-fetch patch needed for a full-registry run into
    the given ExitStack. A single `with a, b, c, ...:` statement can't hold
    this many context managers at once — CPython's compiler caps nested
    blocks — so patches are entered dynamically instead."""
    stack.enter_context(patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry))
    stack.enter_context(patch("job_scraper.pipeline.robots_allowed", return_value=True))
    stack.enter_context(patch("job_scraper.pipeline.fetch_page", side_effect=fixture_fetch_page))
    for module in _ALL_SITE_MODULES:
        stack.enter_context(
            patch(f"job_scraper.sites.{module}.fetch_page", side_effect=fixture_fetch_page)
        )
    stack.enter_context(
        patch("job_scraper.sites.stone_interim.Fetcher.post", return_value=stone_interim_response)
    )


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
        "iamexpat": FixtureAwareIamexpatAdapter,
        "djinni": FixtureAwareDjinniAdapter,
        "arc_dev": ArcDevAdapter,
        "freelancer_com": FixtureAwareFreelancerComAdapter,
        "guru": FixtureAwareGuruAdapter,
        "planet_interim": FixtureAwarePlanetInterimAdapter,
        "ictergezocht": FixtureAwareIctergezochtAdapter,
        "wearedevelopers": FixtureAwareWearedevelopersAdapter,
        "working_nomads": FixtureAwareWorkingNomadsAdapter,
        "freelancermap": FixtureAwareFreelancermapAdapter,
    }

    stone_interim_response = MagicMock()
    stone_interim_response.body = load_fixture_bytes(
        "stone_interim", "listing_api_GetOverviewItems.json"
    )

    with contextlib.ExitStack() as stack:
        _patch_all_sites(stack, fake_registry, fixture_fetch_page, stone_interim_response)
        # robots_allowed is mocked to always return True above: this test cares
        # about adapter/pipeline behavior against fixtures, not live robots.txt
        # fetch results for 20 real domains — it must never make a real request.
        # ignore_robots=True is kept as a belt-and-braces guard in case that
        # mock is ever removed by mistake.
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
    with contextlib.ExitStack() as stack:
        _patch_all_sites(stack, fake_registry, fixture_fetch_page, stone_interim_response)
        results_second = run(ALL_SITE_IDS, repo, str(jobs_dir), ignore_robots=True)

    # On the second run, nothing should change (idempotence)
    for site_id in ALL_SITE_IDS:
        assert results_second[site_id]["written"] == 0, (
            f"Second run should not write any new {site_id} postings, got {results_second[site_id]}"
        )
        assert results_second[site_id]["seen"] == results_first[site_id]["seen"]
