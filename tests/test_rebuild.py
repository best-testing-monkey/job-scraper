import pytest
from pathlib import Path
from job_scraper.core.rebuild import rebuild_site, NOT_REBUILDABLE
from job_scraper.core.db import JobRepository
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.markdown_export import filename_for, slugify
from job_scraper.sites.pro_act import ProActAdapter


@pytest.fixture
def fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "pro_act"


@pytest.fixture
def detail_html(fixture_dir: Path) -> bytes:
    return (fixture_dir / "detail_8887.html").read_bytes()


@pytest.fixture
def tmp_db(tmp_path: Path) -> JobRepository:
    db_path = tmp_path / "test.db"
    repo = JobRepository(str(db_path))
    return repo


@pytest.fixture
def tmp_dirs(tmp_path: Path) -> tuple[str, str, str]:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")
    return jobs_dir, raw_dir, db_path


def test_rebuild_site_not_rebuildable_working_nomads(tmp_db: JobRepository, tmp_dirs: tuple) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs
    with pytest.raises(ValueError, match="working_nomads"):
        rebuild_site("working_nomads", tmp_db, jobs_dir, raw_dir)


def test_rebuild_site_not_rebuildable_stone_interim(tmp_db: JobRepository, tmp_dirs: tuple) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs
    assert "stone_interim" in NOT_REBUILDABLE
    with pytest.raises(ValueError, match="stone_interim"):
        rebuild_site("stone_interim", tmp_db, jobs_dir, raw_dir)


def test_rebuild_site_not_rebuildable_tender_link(tmp_db: JobRepository, tmp_dirs: tuple) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs
    with pytest.raises(ValueError, match="tender_link"):
        rebuild_site("tender_link", tmp_db, jobs_dir, raw_dir)


def test_rebuild_site_unknown_site_id(tmp_db: JobRepository, tmp_dirs: tuple) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs
    with pytest.raises(ValueError, match="not in SITE_REGISTRY"):
        rebuild_site("nonexistent_site", tmp_db, jobs_dir, raw_dir)


def test_rebuild_site_no_raw_dir(tmp_db: JobRepository, tmp_dirs: tuple) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs
    result = rebuild_site("pro_act", tmp_db, jobs_dir, raw_dir)
    assert result == {"rebuilt": 0, "skipped_no_db": 0, "skipped_duplicate": 0, "excluded": 0, "errors": 0}


def test_rebuild_site_skipped_no_db(tmp_db: JobRepository, tmp_dirs: tuple, detail_html: bytes) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    result = rebuild_site("pro_act", tmp_db, jobs_dir, raw_dir)

    assert result["skipped_no_db"] == 1
    assert result["rebuilt"] == 0
    assert result["excluded"] == 0
    assert result["errors"] == 0


def test_rebuild_site_basic_rebuild(tmp_path: Path, detail_html: bytes) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="OLD DESCRIPTION",
    )

    old_markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    old_markdown_file.parent.mkdir(parents=True, exist_ok=True)
    old_markdown_file.write_text("# Agile Coach\n\n## Description\n\nOLD")

    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["rebuilt"] == 1
    assert result["skipped_no_db"] == 0
    assert result["excluded"] == 0
    assert result["errors"] == 0

    updated_markdown_content = old_markdown_file.read_text()
    assert "OLD" not in updated_markdown_content
    assert "Agile Coach" in updated_markdown_content

    cursor = repo.conn.cursor()
    row = cursor.execute(
        "SELECT description, last_seen_at FROM jobs WHERE site_id = ? AND listing_id = ?",
        ("pro_act", "8887")
    ).fetchone()

    assert row is not None
    description, last_seen_at_from_db = row
    assert "OLD" not in description
    assert last_seen_at_from_db == seen_at


def test_rebuild_site_skipped_duplicate(tmp_path: Path, detail_html: bytes) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    original_posting = JobPosting(
        site_id="pro_act",
        listing_id="8886",
        source_url="https://pro-act.nl/vacatures/agile-coach-original/",
        title="Agile Coach",
        description="ORIGINAL",
    )
    repo.upsert(original_posting, seen_at="2026-09-01T10:00:00Z")

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="OLD DESCRIPTION",
    )
    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    repo.set_duplicate_of("pro_act", "8887", 1)

    old_markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    old_markdown_file.parent.mkdir(parents=True, exist_ok=True)
    old_markdown_file.write_text("# Agile Coach\n\n## Description\n\nOLD")

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["skipped_duplicate"] == 1
    assert result["rebuilt"] == 0

    old_content = old_markdown_file.read_text()
    assert "OLD" in old_content


def test_rebuild_site_excluded(tmp_path: Path, detail_html: bytes, monkeypatch) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="ORIGINAL",
    )

    old_markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    old_markdown_file.parent.mkdir(parents=True, exist_ok=True)
    old_markdown_file.write_text("# Agile Coach\n\n## Description\n\nOLD")

    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    def mock_parse_detail(self, stub, page):
        return JobPosting(
            site_id="pro_act",
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=stub.title,
            description="zzp niet toegestaan - excluded",
        )

    import job_scraper.sites.pro_act
    monkeypatch.setattr(job_scraper.sites.pro_act.ProActAdapter, "parse_detail", mock_parse_detail)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["excluded"] == 1
    assert result["rebuilt"] == 0


def test_rebuild_site_parse_error(tmp_path: Path, monkeypatch) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="ORIGINAL",
    )

    old_markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    old_markdown_file.parent.mkdir(parents=True, exist_ok=True)
    old_markdown_file.write_text("# Agile Coach\n\n## Description\n\nOLD")

    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(b"<invalid>html</invalid>")

    def mock_parse_detail(self, stub, page):
        raise ValueError("Parsing failed")

    import job_scraper.sites.pro_act
    monkeypatch.setattr(job_scraper.sites.pro_act.ProActAdapter, "parse_detail", mock_parse_detail)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["errors"] == 1
    assert result["rebuilt"] == 0


def test_rebuild_site_returns_correct_keys(tmp_db: JobRepository, tmp_dirs: tuple) -> None:
    jobs_dir, raw_dir, _ = tmp_dirs
    result = rebuild_site("pro_act", tmp_db, jobs_dir, raw_dir)

    assert set(result.keys()) == {"rebuilt", "skipped_no_db", "skipped_duplicate", "excluded", "errors"}
    assert all(isinstance(v, int) for v in result.values())


def test_rebuild_site_preserves_stale_state_with_date(tmp_path: Path, detail_html: bytes) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="OLD DESCRIPTION",
    )

    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    # Mark it as stale with a date
    repo.set_stale_state("pro_act", "8887", 1, "2026-10-03")

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["rebuilt"] == 1

    # Check DB state: should still be stale with the same date
    cursor = repo.conn.cursor()
    row = cursor.execute(
        "SELECT is_stale, stale_since FROM jobs WHERE site_id = ? AND listing_id = ?",
        ("pro_act", "8887")
    ).fetchone()
    assert row is not None
    is_stale, stale_since = row
    assert is_stale == 1
    assert stale_since == "2026-10-03"

    # Check markdown: should contain the stale since bullet
    markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    markdown_content = markdown_file.read_text()
    assert "- Stale since: 2026-10-03" in markdown_content


def test_rebuild_site_preserves_non_stale_state(tmp_path: Path, detail_html: bytes) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="OLD DESCRIPTION",
    )

    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    # Make sure it's not stale
    repo.set_stale_state("pro_act", "8887", 0, None)

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["rebuilt"] == 1

    # Check DB state: should still be non-stale
    cursor = repo.conn.cursor()
    row = cursor.execute(
        "SELECT is_stale, stale_since FROM jobs WHERE site_id = ? AND listing_id = ?",
        ("pro_act", "8887")
    ).fetchone()
    assert row is not None
    is_stale, stale_since = row
    assert is_stale == 0
    assert stale_since is None

    # Check markdown: should NOT contain stale since bullet
    markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    markdown_content = markdown_file.read_text()
    assert "- Stale since:" not in markdown_content


def test_rebuild_site_preserves_stale_without_date(tmp_path: Path, detail_html: bytes) -> None:
    jobs_dir = str(tmp_path / "jobs")
    raw_dir = str(tmp_path / "raw")
    db_path = str(tmp_path / "test.db")

    repo = JobRepository(db_path)

    initial_posting = JobPosting(
        site_id="pro_act",
        listing_id="8887",
        source_url="https://pro-act.nl/vacatures/agile-coach-8887/",
        title="Agile Coach",
        description="OLD DESCRIPTION",
    )

    seen_at = "2026-09-15T10:00:00Z"
    repo.upsert(initial_posting, seen_at=seen_at)

    # Mark it as stale WITHOUT a date (pre-migration data)
    repo.set_stale_state("pro_act", "8887", 1, None)

    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    site_raw_dir = Path(raw_dir) / "pro_act"
    site_raw_dir.mkdir(parents=True, exist_ok=True)
    (site_raw_dir / "pro_act-8887-agile-coach.html").write_bytes(detail_html)

    result = rebuild_site("pro_act", repo, jobs_dir, raw_dir)

    assert result["rebuilt"] == 1

    # Check DB state: should still be stale without date
    cursor = repo.conn.cursor()
    row = cursor.execute(
        "SELECT is_stale, stale_since FROM jobs WHERE site_id = ? AND listing_id = ?",
        ("pro_act", "8887")
    ).fetchone()
    assert row is not None
    is_stale, stale_since = row
    assert is_stale == 1
    assert stale_since is None

    # Check markdown: should NOT contain stale since bullet (no date)
    markdown_file = Path(jobs_dir) / filename_for(initial_posting)
    markdown_content = markdown_file.read_text()
    assert "- Stale since:" not in markdown_content
