from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch
import tempfile
import re

import pytest

from job_scraper.core.db import JobRepository
from job_scraper.core.models import ListingStub, JobPosting
from job_scraper.pipeline import run
from job_scraper.sites.pro_act import ProActAdapter
from job_scraper.sites.hero import HeroAdapter
from job_scraper.sites.flexvalue import FlexValueAdapter
from job_scraper.sites.base import SiteAdapter


def load_fixture(site_id: str, filename: str) -> str:
    """Load HTML fixture from tests/fixtures/<site_id>/<filename>."""
    fixture_path = Path(__file__).parent / "fixtures" / site_id / filename
    return fixture_path.read_text(encoding="utf-8")


class FixtureAwareProActAdapter(ProActAdapter):
    """Wrapper adapter that fetches listing page and passes it to list_postings."""

    def list_postings(self) -> Iterator[ListingStub]:
        listing_html = load_fixture("pro_act", "listing.html")
        # Only yield postings that have fixture detail pages
        for stub in super().list_postings(listing_html):
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
    """Wrapper adapter that fetches listing page and passes it to list_postings."""

    def list_postings(self) -> Iterator[ListingStub]:
        listing_html = load_fixture("hero", "listing.html")
        # Only yield postings that have fixture detail pages
        for stub in super().list_postings(listing_html):
            if stub.listing_id == "e98187b8":  # We have detail_e98187b8.html
                yield stub


class FixtureAwareFlexValueAdapter(FlexValueAdapter):
    """Wrapper adapter that sets page before calling list_postings."""

    def list_postings(self) -> Iterator[ListingStub]:
        listing_html = load_fixture("flexvalue", "listing.html")
        self.page = listing_html
        # Only yield postings that have fixture detail pages
        for stub in super().list_postings():
            if stub.listing_id == "1065407":  # We have detail_1065407.html
                yield stub


@pytest.fixture
def fixture_fetch_page():
    """Create a monkeypatch function for fetch_page that returns fixture HTML."""

    def mock_fetch_page(strategy: Any, url: str) -> str:
        """Return fixture HTML for detail pages based on URL."""
        if "pro-act.nl" in url and "8887" in url:
            return load_fixture("pro_act", "detail_8887.html")
        elif "hero.eu" in url and "e98187b8" in url:
            return load_fixture("hero", "detail_e98187b8.html")
        elif "flexvalue" in url and "1065407" in url:
            return load_fixture("flexvalue", "detail_1065407.html")
        # Return empty HTML for URLs we don't have fixtures for
        return "<html></html>"

    return mock_fetch_page


def test_integration_end_to_end(tmp_path: Path, fixture_fetch_page: Any) -> None:
    """End-to-end integration test: scrape all 3 sites, verify output and idempotence."""
    db_path = tmp_path / "scraper.db"
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    repo = JobRepository(str(db_path))

    # First run: scrape all sites from fixtures
    fake_registry = {
        "pro_act": FixtureAwareProActAdapter,
        "hero": FixtureAwareHeroAdapter,
        "flexvalue": FixtureAwareFlexValueAdapter,
    }

    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry):
        with patch("job_scraper.pipeline.fetch_page", side_effect=fixture_fetch_page):
            results_first = run(["pro_act", "hero", "flexvalue"], repo, str(jobs_dir))

    # Assertions for first run
    assert "pro_act" in results_first
    assert "hero" in results_first
    assert "flexvalue" in results_first

    # Each site should have at least 1 posting written
    assert results_first["pro_act"]["written"] >= 1, f"pro_act should write at least 1 posting, got {results_first['pro_act']}"
    assert results_first["hero"]["written"] >= 1, "hero should write at least 1 posting"
    assert results_first["flexvalue"]["written"] >= 1, "flexvalue should write at least 1 posting"

    # Each site should have seen at least 1 posting
    assert results_first["pro_act"]["seen"] >= 1
    assert results_first["hero"]["seen"] >= 1
    assert results_first["flexvalue"]["seen"] >= 1

    # Check that markdown files were created for at least one posting per site
    pro_act_files = list(jobs_dir.glob("pro_act-*.md"))
    hero_files = list(jobs_dir.glob("hero-*.md"))
    flexvalue_files = list(jobs_dir.glob("flexvalue-*.md"))

    assert len(pro_act_files) >= 1, f"Expected at least 1 pro_act markdown file, found {len(pro_act_files)}"
    assert len(hero_files) >= 1, f"Expected at least 1 hero markdown file, found {len(hero_files)}"
    assert len(flexvalue_files) >= 1, f"Expected at least 1 flexvalue markdown file, found {len(flexvalue_files)}"

    # Verify that markdown files contain expected content
    assert any(f.exists() for f in pro_act_files), "pro_act markdown files should exist"
    assert any(f.exists() for f in hero_files), "hero markdown files should exist"
    assert any(f.exists() for f in flexvalue_files), "flexvalue markdown files should exist"

    # Second run: run again with same fixtures, verify idempotence
    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry):
        with patch("job_scraper.pipeline.fetch_page", side_effect=fixture_fetch_page):
            results_second = run(["pro_act", "hero", "flexvalue"], repo, str(jobs_dir))

    # On the second run, nothing should change (idempotence)
    assert results_second["pro_act"]["written"] == 0, "Second run should not write any new postings"
    assert results_second["hero"]["written"] == 0, "Second run should not write any new postings"
    assert results_second["flexvalue"]["written"] == 0, "Second run should not write any new postings"

    # But we should still see the same number of postings
    assert results_second["pro_act"]["seen"] == results_first["pro_act"]["seen"]
    assert results_second["hero"]["seen"] == results_first["hero"]["seen"]
    assert results_second["flexvalue"]["seen"] == results_first["flexvalue"]["seen"]
