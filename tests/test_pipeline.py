from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch
import tempfile
import subprocess
import sys

import pytest

from job_scraper.core.db import JobRepository
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.pipeline import fetch_page, run, run_site
from job_scraper.sites.base import FetchStrategy, SiteAdapter


class FakeAdapter(SiteAdapter):
    site_id = "fake-site"
    base_url = "https://fake-site.example.com"
    fetch_strategy = FetchStrategy.STATIC

    def list_postings(self) -> Iterator[ListingStub]:
        yield ListingStub(
            listing_id="job-1",
            detail_url="https://fake-site.example.com/job/1",
            title="Python Developer",
        )
        yield ListingStub(
            listing_id="job-2",
            detail_url="https://fake-site.example.com/job/2",
            title="Senior Developer",
        )
        yield ListingStub(
            listing_id="job-3",
            detail_url="https://fake-site.example.com/job/3",
            title="Contractor Role (no zzp niet toegestaan here)",
        )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        if stub.listing_id == "job-1":
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
                client="Acme Corp",
                description="A great opportunity for a Python developer",
            )
        elif stub.listing_id == "job-2":
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
                client="Tech Startup",
                description="zzp niet toegestaan - this is excluded",
            )
        elif stub.listing_id == "job-3":
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
                client="Contractor Company",
                description="An independent contracting opportunity",
            )


def test_fetch_page_static() -> None:
    class FakeResponse:
        html_content = "<html>test</html>"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        result = fetch_page(FetchStrategy.STATIC, "https://example.com")
        assert result == "<html>test</html>"
        mock_get.assert_called_once_with("https://example.com")


def test_fetch_page_stealth_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="stealth"):
        fetch_page(FetchStrategy.STEALTH, "https://example.com")


def test_fetch_page_dynamic_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="dynamic"):
        fetch_page(FetchStrategy.DYNAMIC, "https://example.com")


def test_run_site_basic(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    repo = JobRepository(str(db_path))

    adapter = FakeAdapter()

    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = None
        counters = run_site(adapter, repo, str(jobs_dir), "2023-01-01T00:00:00")

    assert counters["seen"] == 3
    assert counters["excluded"] == 1
    assert counters["duplicates"] == 0
    assert counters["written"] == 2
    assert counters["stale_marked"] == 0

    assert (jobs_dir / "fake-site-job-1-python-developer.md").exists()
    assert (jobs_dir / "fake-site-job-3-contractor-role-no-zzp-niet-toegestaan-here.md").exists()


def test_run_site_with_duplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    repo = JobRepository(str(db_path))

    adapter = FakeAdapter()

    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = None

        first_run = run_site(adapter, repo, str(jobs_dir), "2023-01-01T00:00:00")
        assert first_run["written"] == 2

        second_run = run_site(adapter, repo, str(jobs_dir), "2023-01-02T00:00:00")
        assert second_run["written"] == 0


def test_run_with_unknown_site() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        repo = JobRepository(str(db_path))

        with patch("job_scraper.pipeline.SITE_REGISTRY", {}):
            results = run(["unknown-site"], repo, tmp_dir)

        assert results == {}


def test_run_with_registry_entry(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    repo = JobRepository(str(db_path))

    fake_registry = {"fake-site": FakeAdapter}

    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry):
        with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
            mock_fetch.return_value = None
            results = run(["fake-site"], repo, str(jobs_dir))

    assert "fake-site" in results
    assert results["fake-site"]["seen"] == 3
    assert results["fake-site"]["excluded"] == 1
    assert results["fake-site"]["written"] == 2


def test_run_with_robots_disallowed(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    repo = JobRepository(str(db_path))

    fake_registry = {"fake-site": FakeAdapter}

    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry):
        with patch("job_scraper.pipeline.robots_allowed") as mock_robots:
            mock_robots.return_value = False
            results = run(["fake-site"], repo, str(tmp_path))

    assert results == {}


def test_run_with_robots_disallowed_but_ignored(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    repo = JobRepository(str(db_path))

    fake_registry = {"fake-site": FakeAdapter}

    with patch("job_scraper.pipeline.SITE_REGISTRY", fake_registry):
        with patch("job_scraper.pipeline.robots_allowed") as mock_robots:
            mock_robots.return_value = False
            with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
                mock_fetch.return_value = None
                results = run(
                    ["fake-site"], repo, str(jobs_dir), ignore_robots=True
                )

    assert "fake-site" in results
    assert results["fake-site"]["seen"] == 3


def test_list_sites_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "job_scraper", "list-sites"],
        cwd="/media/baz/MonkeyWorks/PycharmProjects/job-hunter/scraper",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
