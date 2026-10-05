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
        body = b"<html>test</html>"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        result = fetch_page(FetchStrategy.STATIC, "https://example.com")
        assert result == b"<html>test</html>"
        mock_get.assert_called_once_with("https://example.com")


def test_fetch_page_stealth() -> None:
    class FakeResponse:
        body = b"<html>stealth test</html>"

    with patch("job_scraper.sites.base.StealthyFetcher.fetch") as mock_fetch:
        mock_fetch.return_value = FakeResponse()
        result = fetch_page(FetchStrategy.STEALTH, "https://example.com")
        assert result == b"<html>stealth test</html>"
        mock_fetch.assert_called_once_with("https://example.com", headless=True)


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
    assert counters["screenshots_skipped"] == 0

    assert (jobs_dir / "fake-site-job-1-python-developer.md").exists()
    assert (jobs_dir / "fake-site-job-3-contractor-role-no-zzp-niet-toegestaan-here.md").exists()


def test_run_site_saves_raw_pages_when_raw_dir_given(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    raw_dir = tmp_path / "raw"
    repo = JobRepository(str(db_path))

    adapter = FakeAdapter()

    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = b"<html>raw page</html>"
        run_site(adapter, repo, str(jobs_dir), "2023-01-01T00:00:00", raw_dir=str(raw_dir))

    # Raw pages are saved unconditionally, including for the excluded job-2
    # posting — filtering logic can change later without losing the source.
    assert (raw_dir / "fake-site" / "fake-site-job-1-python-developer.html").read_bytes() == (
        b"<html>raw page</html>"
    )
    assert (raw_dir / "fake-site" / "fake-site-job-2-senior-developer.html").exists()
    assert (raw_dir / "fake-site" / "fake-site-job-3-contractor-role-no-zzp-niet-toegestaan-here.html").exists()


def test_run_site_skips_raw_storage_when_raw_dir_none(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    raw_dir = tmp_path / "raw"
    repo = JobRepository(str(db_path))

    adapter = FakeAdapter()

    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = b"<html>raw page</html>"
        run_site(adapter, repo, str(jobs_dir), "2023-01-01T00:00:00")

    assert not raw_dir.exists()


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
        with patch("job_scraper.pipeline.robots_allowed", return_value=True):
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


# --- screenshots (E13-S24) ---

_STEM1 = "fake-site-job-1-python-developer"


def _run_shots(tmp_path: Path, adapter: SiteAdapter, shots: str | None, **patch_kw: Any):
    repo = JobRepository(str(tmp_path / "test.db"))
    with (
        patch("job_scraper.pipeline.fetch_page", return_value=None),
        patch("job_scraper.pipeline.capture_element", **patch_kw) as cap,
    ):
        counters = run_site(
            adapter, repo, str(tmp_path / "jobs"), "2023-01-01T00:00:00", screenshots_dir=shots
        )
    return counters, cap


class ShotAdapter(FakeAdapter):
    screenshot_selector = "div.desc"


def test_screenshot_success(tmp_path: Path) -> None:
    shots = str(tmp_path / "shots")
    counters, cap = _run_shots(tmp_path, ShotAdapter(), shots, return_value=True)
    assert cap.call_args_list[0].args[2] == f"{shots}/{_STEM1}.png"
    assert cap.call_args_list[0].args[:2] == ("https://fake-site.example.com/job/1", "div.desc")
    md = (tmp_path / "jobs" / f"{_STEM1}.md").read_text()
    assert f"- Screenshot: screenshots/{_STEM1}.png" in md
    assert counters["screenshots_taken"] == 2
    assert counters["screenshots_failed"] == 0


def test_screenshot_false(tmp_path: Path) -> None:
    counters, _ = _run_shots(tmp_path, ShotAdapter(), str(tmp_path / "shots"), return_value=False)
    md = (tmp_path / "jobs" / f"{_STEM1}.md").read_text()
    assert "- Screenshot:" not in md
    assert counters["written"] == 2
    assert counters["screenshots_failed"] == 2


def test_screenshot_raises(tmp_path: Path) -> None:
    counters, _ = _run_shots(
        tmp_path, ShotAdapter(), str(tmp_path / "shots"), side_effect=RuntimeError("boom")
    )
    assert counters["written"] == 2
    assert counters["screenshots_failed"] == 2


def test_screenshot_existing_png_kept(tmp_path: Path) -> None:
    shots = tmp_path / "shots"
    shots.mkdir()
    (shots / f"{_STEM1}.png").write_bytes(b"png")
    _run_shots(tmp_path, ShotAdapter(), str(shots), return_value=False)
    md = (tmp_path / "jobs" / f"{_STEM1}.md").read_text()
    assert f"- Screenshot: screenshots/{_STEM1}.png" in md


def test_screenshot_dir_none_no_capture(tmp_path: Path) -> None:
    counters, cap = _run_shots(tmp_path, ShotAdapter(), None, return_value=True)
    cap.assert_not_called()
    assert counters["screenshots_taken"] == 0
    assert counters["screenshots_failed"] == 0


def test_screenshot_hide_selectors_passed(tmp_path: Path) -> None:
    class HideShot(ShotAdapter):
        screenshot_hide_selectors = ("div.form", "#banner")

    _, cap = _run_shots(tmp_path, HideShot(), str(tmp_path / "shots"), return_value=True)
    assert cap.call_args_list[0].kwargs["hide_selectors"] == HideShot.screenshot_hide_selectors


def test_screenshot_no_selector_no_capture(tmp_path: Path) -> None:
    _, cap = _run_shots(tmp_path, FakeAdapter(), str(tmp_path / "shots"), return_value=True)
    cap.assert_not_called()


def test_screenshot_stealth_flag(tmp_path: Path) -> None:
    class StealthShot(ShotAdapter):
        fetch_strategy = FetchStrategy.STEALTH

    _, cap = _run_shots(tmp_path, StealthShot(), str(tmp_path / "s1"), return_value=True)
    assert all(c.kwargs["stealth"] is True for c in cap.call_args_list)
    (tmp_path / "b").mkdir()
    _, cap = _run_shots(tmp_path / "b", ShotAdapter(), str(tmp_path / "s2"), return_value=True)
    assert all(c.kwargs["stealth"] is False for c in cap.call_args_list)


def test_screenshot_none_counts_skipped(tmp_path: Path) -> None:
    shots = str(tmp_path / "shots")
    counters, cap = _run_shots(tmp_path, ShotAdapter(), shots, return_value=None)
    assert counters["screenshots_skipped"] == 2
    assert counters["screenshots_failed"] == 0
    assert counters["screenshots_taken"] == 0
    md = (tmp_path / "jobs" / f"{_STEM1}.md").read_text()
    assert "- Screenshot:" not in md
    assert counters["written"] == 2


def test_screenshot_pre_actions_and_skip_selectors_passed(tmp_path: Path) -> None:
    class PreActionSkipAdapter(ShotAdapter):
        screenshot_pre_actions = ("click:button.load", "wait:div.content")
        screenshot_skip_selectors = ("div.no-ad", "span.skip")

    _, cap = _run_shots(tmp_path, PreActionSkipAdapter(), str(tmp_path / "shots"), return_value=True)
    assert cap.call_args_list[0].kwargs["pre_actions"] == PreActionSkipAdapter.screenshot_pre_actions
    assert cap.call_args_list[0].kwargs["skip_selectors"] == PreActionSkipAdapter.screenshot_skip_selectors


def test_screenshot_not_for_excluded_or_duplicates(tmp_path: Path) -> None:
    # FakeAdapter: job-2 excluded -> only 2 captures, none for job-2
    _, cap = _run_shots(tmp_path, ShotAdapter(), str(tmp_path / "shots"), return_value=True)
    urls = [c.args[0] for c in cap.call_args_list]
    assert "https://fake-site.example.com/job/2" not in urls

    class DupAdapter(ShotAdapter):
        def list_postings(self) -> Iterator[ListingStub]:
            yield ListingStub("a", "https://x/a", "Same Title")
            yield ListingStub("b", "https://x/b", "Same Title")

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return JobPosting(
                site_id=self.site_id, listing_id=stub.listing_id, source_url=stub.detail_url,
                title="Same Title", client="Acme", description="desc",
            )

    (tmp_path / "d").mkdir()
    counters, cap = _run_shots(tmp_path / "d", DupAdapter(), str(tmp_path / "s3"), return_value=True)
    assert counters["duplicates"] == 1
    assert cap.call_count == 1


class StaleAdapter(SiteAdapter):
    site_id = "stale-site"
    base_url = "https://stale-site.example.com"
    fetch_strategy = FetchStrategy.STATIC

    def __init__(
        self, ids: list[str], descs: dict[str, str] | None = None, dups: tuple[str, ...] = ()
    ) -> None:
        self.dups = dups
        self.ids = ids
        self.descs = descs or {}

    def list_postings(self) -> Iterator[ListingStub]:
        for i in self.ids:
            yield ListingStub(
                listing_id=i,
                detail_url=f"https://stale-site.example.com/{i}",
                title="Dup Role" if i in self.dups else f"Role {i}",
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        return JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=stub.title,
            client="Acme",
            description=self.descs.get(stub.listing_id, f"Description of {stub.listing_id}"),
        )


def _stale_run(repo, jobs, adapter, n: int, today: str) -> dict:
    with patch("job_scraper.pipeline.fetch_page", return_value=None):
        return run_site(adapter, repo, str(jobs), f"2023-01-0{n}T00:00:00", today=today)


def test_stale_since_lifecycle(tmp_path: Path) -> None:
    repo = JobRepository(str(tmp_path / "t.db"))
    jobs = tmp_path / "jobs"
    a_md = jobs / "stale-site-A-role-a.md"
    b_md = jobs / "stale-site-B-role-b.md"

    _stale_run(repo, jobs, StaleAdapter(["A", "B"]), 1, "2026-10-01")
    assert "Stale since" not in b_md.read_text()

    c = _stale_run(repo, jobs, StaleAdapter(["A"]), 2, "2026-10-05")
    assert c["newly_stale"] == 1 and c["stale_marked"] == 1
    assert b_md.read_text().count("- Stale since: 2026-10-05") == 1
    assert "Stale since" not in a_md.read_text()

    c = _stale_run(repo, jobs, StaleAdapter(["A"]), 3, "2026-10-08")
    assert c["newly_stale"] == 0
    assert b_md.read_text().count("- Stale since:") == 1
    assert "- Stale since: 2026-10-05" in b_md.read_text()

    _stale_run(repo, jobs, StaleAdapter(["A", "B"]), 4, "2026-10-09")
    assert "Stale since" not in b_md.read_text()
    row = repo.conn.execute("SELECT is_stale FROM jobs WHERE listing_id = 'B'").fetchone()
    assert row[0] == 0

    _stale_run(repo, jobs, StaleAdapter(["A"]), 5, "2026-10-10")
    assert "- Stale since: 2026-10-10" in b_md.read_text()
    _stale_run(repo, jobs, StaleAdapter(["A", "B"], {"B": "New text"}), 6, "2026-10-11")
    text = b_md.read_text()
    assert "Stale since" not in text and "New text" in text


def test_stale_duplicate_gets_no_bullet(tmp_path: Path) -> None:
    repo = JobRepository(str(tmp_path / "t.db"))
    jobs = tmp_path / "jobs"
    adapter = StaleAdapter(["A", "B"], dups=("A", "B"))
    _stale_run(repo, jobs, adapter, 1, "2026-10-01")
    files = sorted(p.name for p in jobs.glob("*.md"))
    assert files == ["stale-site-A-dup-role.md"]
    c = _stale_run(repo, jobs, StaleAdapter(["A"], dups=("A",)), 2, "2026-10-05")
    assert c["newly_stale"] == 0
    assert sorted(p.name for p in jobs.glob("*.md")) == files
    assert "Stale since" not in (jobs / files[0]).read_text()


def test_reseen_posting_not_duplicate_of_itself(tmp_path: Path) -> None:
    repo = JobRepository(str(tmp_path / "t.db"))
    jobs = tmp_path / "jobs"
    first = _stale_run(repo, jobs, StaleAdapter(["A", "B"]), 1, "2026-10-01")
    second = _stale_run(repo, jobs, StaleAdapter(["A", "B"]), 2, "2026-10-02")
    assert first["duplicates"] == 0 and first["written"] == 2
    assert second["duplicates"] == 0 and second["written"] == 0
    assert repo.conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE duplicate_of IS NOT NULL").fetchone()[0] == 0


class BoomAdapter(SiteAdapter):
    site_id = "boom-site"
    base_url = "https://boom.example.com"
    fetch_strategy = FetchStrategy.STATIC

    def list_postings(self) -> Iterator[ListingStub]:
        raise RuntimeError("boom")
        yield  # pragma: no cover

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        raise NotImplementedError


class PartialAdapter(FakeAdapter):
    site_id = "partial-site"

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


def test_run_survives_site_exception(tmp_path: Path, capsys) -> None:
    repo = JobRepository(str(tmp_path / "test.db"))
    registry = {"boom-site": BoomAdapter, "fake-site": FakeAdapter}
    calls: list[tuple[str, dict]] = []

    with patch("job_scraper.pipeline.SITE_REGISTRY", registry):
        with patch("job_scraper.pipeline.robots_allowed", return_value=True):
            with patch("job_scraper.pipeline.fetch_page", return_value=None):
                results = run(
                    ["boom-site", "fake-site"],
                    repo,
                    str(tmp_path / "jobs"),
                    on_site_done=lambda sid, c: calls.append((sid, c)),
                )

    assert set(results) == {"boom-site", "fake-site"}
    assert results["boom-site"]["error"].startswith("RuntimeError: boom")
    assert results["fake-site"]["seen"] == 3
    assert "error" not in results["fake-site"]
    assert [sid for sid, _ in calls] == ["boom-site", "fake-site"]
    assert "Error: site boom-site failed: RuntimeError: boom" in capsys.readouterr().err


def test_run_error_keeps_partial_counters(tmp_path: Path) -> None:
    repo = JobRepository(str(tmp_path / "test.db"))
    registry = {"partial-site": PartialAdapter}
    state = {"n": 0}

    def fake_fetch(strategy, url):
        state["n"] += 1
        if state["n"] == 2:
            raise TimeoutError("curl timeout")
        return None

    with patch("job_scraper.pipeline.SITE_REGISTRY", registry):
        with patch("job_scraper.pipeline.robots_allowed", return_value=True):
            with patch("job_scraper.pipeline.fetch_page", side_effect=fake_fetch):
                results = run(["partial-site"], repo, str(tmp_path / "jobs"))

    assert results["partial-site"]["seen"] == 2
    assert results["partial-site"]["error"] == "TimeoutError: curl timeout"


def test_source_url_changed_rewrites_markdown(tmp_path: Path) -> None:
    """When posting content is unchanged but source_url differs, the file is rewritten."""
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    repo = JobRepository(str(db_path))

    # Create an adapter that returns job-1 with a new source URL
    class ChangedUrlAdapter(FakeAdapter):
        def parse_detail(self, stub: Any, page: Any) -> JobPosting:
            if stub.listing_id == "job-1":
                return JobPosting(
                    site_id=self.site_id,
                    listing_id=stub.listing_id,
                    source_url="https://new-example.com/job/1",  # New URL
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

    adapter = ChangedUrlAdapter()

    # First run: establish baseline with old URL
    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = None
        first_run = run_site(
            adapter, repo, str(jobs_dir), "2023-01-01T00:00:00"
        )

    assert first_run["written"] == 2
    md_path = jobs_dir / "fake-site-job-1-python-developer.md"
    assert md_path.exists()
    content_after_first = md_path.read_text()
    assert "- Source: https://new-example.com/job/1" in content_after_first

    # Second run: same content, same URL -> nothing written
    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = None
        second_run = run_site(
            adapter, repo, str(jobs_dir), "2023-01-02T00:00:00"
        )

    assert second_run["written"] == 0
    content_after_second = md_path.read_text()
    assert content_after_second == content_after_first


def test_source_url_differs_when_unchanged_content(tmp_path: Path) -> None:
    """Pre-write markdown with old source URL, upsert posting, then run_site should rewrite."""
    db_path = tmp_path / "test.db"
    jobs_dir = tmp_path / "jobs"
    repo = JobRepository(str(db_path))

    # Create the markdown file and upsert with old source URL first
    old_url = "https://old.example/job/go/1"
    new_url = "https://new.example/job/1"

    posting_old = JobPosting(
        site_id="fake-site",
        listing_id="job-1",
        source_url=old_url,
        title="Python Developer",
        client="Acme Corp",
        description="A great opportunity for a Python developer",
    )

    jobs_dir.mkdir(parents=True, exist_ok=True)
    md_path = jobs_dir / "fake-site-job-1-python-developer.md"
    from job_scraper.core.markdown_export import render
    md_path.write_text(render(posting_old))

    # Upsert the posting with the OLD URL to establish a baseline
    repo.upsert(posting_old, seen_at="2023-01-01T00:00:00")

    # Now create a posting with the same content but NEW URL
    posting_new = JobPosting(
        site_id="fake-site",
        listing_id="job-1",
        source_url=new_url,  # New URL
        title="Python Developer",
        client="Acme Corp",
        description="A great opportunity for a Python developer",
    )

    # Verify the content hashes are the same (source_url is not included in hash)
    assert posting_old.content_hash() == posting_new.content_hash()

    # Create an adapter that returns only the one posting with new URL
    class NewUrlAdapter(SiteAdapter):
        site_id = "fake-site"
        base_url = "https://fake-site.example.com"
        fetch_strategy = FetchStrategy.STATIC

        def list_postings(self) -> Iterator[ListingStub]:
            yield ListingStub(
                listing_id="job-1",
                detail_url="https://fake-site.example.com/job/1",
                title="Python Developer",
            )

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return posting_new

    adapter = NewUrlAdapter()

    # Run the scraper: should detect source URL differs and rewrite
    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = None
        counters = run_site(adapter, repo, str(jobs_dir), "2023-01-02T00:00:00")

    assert counters["written"] == 1  # Should write 1 for the URL change
    content = md_path.read_text()
    assert f"- Source: {new_url}" in content
    assert f"- Source: {old_url}" not in content

    # Second run: URL is same -> nothing written
    with patch("job_scraper.pipeline.fetch_page") as mock_fetch:
        mock_fetch.return_value = None
        counters = run_site(adapter, repo, str(jobs_dir), "2023-01-03T00:00:00")

    assert counters["written"] == 0
