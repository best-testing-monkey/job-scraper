import pytest

from job_scraper.core import markdown_export
from job_scraper.core.db import JobRepository
from job_scraper.core.models import JobPosting
from job_scraper.core.stale_sync import sync_stale_markers

COUNTER_KEYS = {"stale_rows", "dated", "written", "cleared", "missing_md"}


@pytest.fixture
def env(tmp_path):
    repo = JobRepository(str(tmp_path / "t.db"))
    jobs = str(tmp_path / "jobs")
    yield repo, jobs
    repo.conn.close()


def add(repo, jobs, lid, title="Dev", is_stale=0, stale_since=None, write_md=True, md_stale=None):
    p = JobPosting(site_id="s", listing_id=lid, source_url=f"http://x/{lid}", title=title, description="d")
    repo.upsert(p, "2026-01-01")
    repo.set_stale_state("s", lid, is_stale, stale_since)
    path = markdown_export.write(p, jobs, stale_since=md_stale) if write_md else None
    return p, path


def test_stale_undated_is_dated_and_written(env):
    repo, jobs = env
    _, path = add(repo, jobs, "1", is_stale=1)
    c = sync_stale_markers(repo, jobs, "2026-10-05")
    assert set(c) == COUNTER_KEYS
    assert c == {"stale_rows": 1, "dated": 1, "written": 1, "cleared": 0, "missing_md": 0}
    assert "- Stale since: 2026-10-05" in open(path).read()
    assert repo.list_stale_state()[0][4] == "2026-10-05"


def test_stale_dated_keeps_date(env):
    repo, jobs = env
    _, path = add(repo, jobs, "1", is_stale=1, stale_since="2026-09-01")
    c = sync_stale_markers(repo, jobs, "2026-10-05")
    assert c["dated"] == 0 and c["written"] == 1
    assert "- Stale since: 2026-09-01" in open(path).read()
    assert repo.list_stale_state()[0][4] == "2026-09-01"


def test_live_row_bullet_removed(env):
    repo, jobs = env
    _, path = add(repo, jobs, "1", is_stale=0, md_stale="2026-09-01")
    assert "Stale since" in open(path).read()
    c = sync_stale_markers(repo, jobs, "2026-10-05")
    assert c["cleared"] == 1 and c["stale_rows"] == 0
    assert "Stale since" not in open(path).read()


def test_missing_md(env):
    repo, jobs = env
    add(repo, jobs, "1", is_stale=1, write_md=False)
    c = sync_stale_markers(repo, jobs, "2026-10-05")
    assert c["missing_md"] == 1 and c["stale_rows"] == 1
    assert c["written"] == 0 and c["cleared"] == 0 and c["dated"] == 0


def test_duplicate_row_ignored(env):
    repo, jobs = env
    add(repo, jobs, "1", is_stale=0)
    add(repo, jobs, "2", title="Other", is_stale=1, write_md=False)
    repo.conn.execute("UPDATE jobs SET duplicate_of = 1 WHERE listing_id = '2'")
    repo.conn.commit()
    c = sync_stale_markers(repo, jobs, "2026-10-05")
    assert c == {"stale_rows": 0, "dated": 0, "written": 0, "cleared": 0, "missing_md": 0}


def test_idempotent(env):
    repo, jobs = env
    _, path = add(repo, jobs, "1", is_stale=1)
    add(repo, jobs, "2", title="Live", is_stale=0, md_stale="2026-09-01")
    sync_stale_markers(repo, jobs, "2026-10-05")
    c = sync_stale_markers(repo, jobs, "2026-12-31")
    assert c["dated"] == 0 and c["written"] == 0 and c["cleared"] == 0
    assert "- Stale since: 2026-10-05" in open(path).read()
