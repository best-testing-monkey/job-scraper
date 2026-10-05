import json
import sqlite3
import pytest
from job_scraper.core.db import JobRepository
from job_scraper.core.models import JobPosting


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    repo = JobRepository(str(db_file))
    yield repo
    repo.conn.close()


def test_upsert_new_posting_returns_true(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="123",
        source_url="https://upwork.com/jobs/123",
        title="Python Developer",
        client="John Doe",
        location="Remote",
        description="Build a web scraper",
    )
    result = temp_db.upsert(posting, "2026-09-27T10:00:00Z")
    assert result is True

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE site_id = ? AND listing_id = ?",
                   ("upwork", "123"))
    row = cursor.fetchone()
    assert row is not None
    assert row[2] == "123"
    assert row[3] == "https://upwork.com/jobs/123"
    assert row[4] == "Python Developer"


def test_upsert_identical_posting_returns_false(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="456",
        source_url="https://upwork.com/jobs/456",
        title="React Developer",
        client="Jane Smith",
        location="NYC",
        description="Build a web app",
    )

    result1 = temp_db.upsert(posting, "2026-09-27T10:00:00Z")
    assert result1 is True

    result2 = temp_db.upsert(posting, "2026-09-27T11:00:00Z")
    assert result2 is False

    cursor = temp_db.conn.cursor()
    cursor.execute(
        "SELECT first_seen_at, last_seen_at FROM jobs WHERE site_id = ? AND listing_id = ?",
        ("upwork", "456"),
    )
    row = cursor.fetchone()
    assert row[0] == "2026-09-27T10:00:00Z"
    assert row[1] == "2026-09-27T11:00:00Z"


def test_upsert_with_changed_description_returns_true(temp_db):
    posting1 = JobPosting(
        site_id="upwork",
        listing_id="789",
        source_url="https://upwork.com/jobs/789",
        title="JavaScript Developer",
        client="Bob Wilson",
        location="London",
        description="Build a frontend app",
    )

    result1 = temp_db.upsert(posting1, "2026-09-27T10:00:00Z")
    assert result1 is True

    posting2 = JobPosting(
        site_id="upwork",
        listing_id="789",
        source_url="https://upwork.com/jobs/789",
        title="JavaScript Developer",
        client="Bob Wilson",
        location="London",
        description="Build a backend app",
    )

    result2 = temp_db.upsert(posting2, "2026-09-27T11:00:00Z")
    assert result2 is True


def test_mark_stale_not_seen_since(temp_db):
    posting1 = JobPosting(
        site_id="upwork",
        listing_id="111",
        source_url="https://upwork.com/jobs/111",
        title="Job 1",
    )
    posting2 = JobPosting(
        site_id="upwork",
        listing_id="222",
        source_url="https://upwork.com/jobs/222",
        title="Job 2",
    )
    posting3 = JobPosting(
        site_id="upwork",
        listing_id="333",
        source_url="https://upwork.com/jobs/333",
        title="Job 3",
    )

    temp_db.upsert(posting1, "2026-09-27T08:00:00Z")
    temp_db.upsert(posting2, "2026-09-27T09:00:00Z")
    temp_db.upsert(posting3, "2026-09-27T11:00:00Z")

    stale_count = temp_db.mark_stale_not_seen_since("upwork", "2026-09-27T10:00:00Z")
    assert stale_count == 2

    cursor = temp_db.conn.cursor()
    cursor.execute(
        "SELECT id, is_stale FROM jobs WHERE site_id = ? ORDER BY listing_id",
        ("upwork",),
    )
    rows = cursor.fetchall()
    assert rows[0][1] == 1
    assert rows[1][1] == 1
    assert rows[2][1] == 0


def test_find_duplicate_case_insensitive(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="dup1",
        source_url="https://upwork.com/jobs/dup1",
        title="Python Developer",
        client="John Doe",
        location="Remote",
    )
    temp_db.upsert(posting, "2026-09-27T10:00:00Z")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE listing_id = ?", ("dup1",))
    expected_id = cursor.fetchone()[0]

    result = temp_db.find_duplicate("python developer", "john doe", "remote")
    assert result == expected_id


def test_find_duplicate_whitespace_normalized(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="dup2",
        source_url="https://upwork.com/jobs/dup2",
        title="Python   Developer",
        client="John    Doe",
        location="  Remote  ",
    )
    temp_db.upsert(posting, "2026-09-27T10:00:00Z")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE listing_id = ?", ("dup2",))
    expected_id = cursor.fetchone()[0]

    result = temp_db.find_duplicate("python developer", "john doe", "remote")
    assert result == expected_id


def test_find_duplicate_no_match(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="dup3",
        source_url="https://upwork.com/jobs/dup3",
        title="Python Developer",
        client="John Doe",
        location="Remote",
    )
    temp_db.upsert(posting, "2026-09-27T10:00:00Z")

    result = temp_db.find_duplicate("Java Developer", "Jane Smith", "NYC")
    assert result is None


def test_find_duplicate_excludes_duplicates(temp_db):
    posting1 = JobPosting(
        site_id="upwork",
        listing_id="original",
        source_url="https://upwork.com/jobs/original",
        title="Python Developer",
        client="John Doe",
        location="Remote",
    )
    posting2 = JobPosting(
        site_id="upwork",
        listing_id="duplicate",
        source_url="https://upwork.com/jobs/duplicate",
        title="Python Developer",
        client="John Doe",
        location="Remote",
    )
    temp_db.upsert(posting1, "2026-09-27T10:00:00Z")
    temp_db.upsert(posting2, "2026-09-27T10:00:00Z")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE listing_id = ?", ("original",))
    original_id = cursor.fetchone()[0]

    temp_db.set_duplicate_of("upwork", "duplicate", original_id)

    result = temp_db.find_duplicate("python developer", "john doe", "remote")
    assert result == original_id


def test_set_duplicate_of(temp_db):
    posting1 = JobPosting(
        site_id="upwork",
        listing_id="orig",
        source_url="https://upwork.com/jobs/orig",
        title="Python Developer",
    )
    posting2 = JobPosting(
        site_id="upwork",
        listing_id="dup",
        source_url="https://upwork.com/jobs/dup",
        title="Python Developer",
    )
    temp_db.upsert(posting1, "2026-09-27T10:00:00Z")
    temp_db.upsert(posting2, "2026-09-27T10:00:00Z")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE listing_id = ?", ("orig",))
    original_id = cursor.fetchone()[0]

    temp_db.set_duplicate_of("upwork", "dup", original_id)

    cursor.execute("SELECT duplicate_of FROM jobs WHERE listing_id = ?", ("dup",))
    dup_row = cursor.fetchone()
    assert dup_row[0] == original_id


def test_skills_stored_as_json(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="skills_test",
        source_url="https://upwork.com/jobs/skills_test",
        title="Python Developer",
        skills=["Python", "Django", "PostgreSQL"],
    )
    temp_db.upsert(posting, "2026-09-27T10:00:00Z")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT skills FROM jobs WHERE listing_id = ?", ("skills_test",))
    row = cursor.fetchone()
    skills = json.loads(row[0])
    assert skills == ["Python", "Django", "PostgreSQL"]


def test_extra_fields_stored_as_json(temp_db):
    posting = JobPosting(
        site_id="upwork",
        listing_id="extra_test",
        source_url="https://upwork.com/jobs/extra_test",
        title="Python Developer",
        extra_fields={"budget": "5000", "duration": "3 months"},
    )
    temp_db.upsert(posting, "2026-09-27T10:00:00Z")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT extra_fields FROM jobs WHERE listing_id = ?", ("extra_test",))
    row = cursor.fetchone()
    extra = json.loads(row[0])
    assert extra == {"budget": "5000", "duration": "3 months"}


def _p(listing_id, title="T", description="d", site="s"):
    return JobPosting(site_id=site, listing_id=listing_id,
                      source_url=f"https://x/{listing_id}", title=title,
                      description=description)


def _stale(repo, lid, site="s"):
    return repo.conn.execute(
        "SELECT is_stale, stale_since FROM jobs WHERE site_id=? AND listing_id=?",
        (site, lid)).fetchone()


def test_migration_adds_stale_since_to_old_db(tmp_path):
    path = str(tmp_path / "old.db")
    raw = sqlite3.connect(path)
    raw.execute("""CREATE TABLE jobs (
        id INTEGER PRIMARY KEY, site_id TEXT NOT NULL, listing_id TEXT NOT NULL,
        source_url TEXT NOT NULL, title TEXT NOT NULL,
        client TEXT, category TEXT, level TEXT, status TEXT, location TEXT,
        hours TEXT, rate TEXT, duration TEXT, posted_date TEXT, experience TEXT,
        skills TEXT, description TEXT, scrape_note TEXT, extra_fields TEXT,
        content_hash TEXT NOT NULL, first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL, is_stale INTEGER NOT NULL DEFAULT 0,
        duplicate_of INTEGER REFERENCES jobs(id), UNIQUE(site_id, listing_id))""")
    raw.execute("INSERT INTO jobs (site_id, listing_id, source_url, title, content_hash,"
                " first_seen_at, last_seen_at) VALUES ('s','1','u','Old','h','a','b')")
    raw.commit()
    raw.close()
    for _ in range(2):
        repo = JobRepository(path)
        cols = [r[1] for r in repo.conn.execute("PRAGMA table_info(jobs)")]
        assert cols.count("stale_since") == 1
        assert repo.conn.execute(
            "SELECT title, stale_since FROM jobs").fetchall() == [("Old", None)]
        repo.conn.close()


@pytest.mark.parametrize("changed", [False, True])
def test_upsert_clears_stale_since(temp_db, changed):
    temp_db.upsert(_p("1"), "2026-10-01T00:00:00Z")
    temp_db.set_stale_state("s", "1", 1, "2026-10-01")
    temp_db.upsert(_p("1", description="new" if changed else "d"), "2026-10-02T00:00:00Z")
    assert _stale(temp_db, "1") == (0, None)


def test_mark_stale_sets_and_keeps_stale_since(temp_db):
    temp_db.upsert(_p("1"), "2026-10-01T00:00:00Z")
    assert temp_db.mark_stale_not_seen_since("s", "2026-10-02T00:00:00Z", "2026-10-02") == 1
    assert _stale(temp_db, "1") == (1, "2026-10-02")
    assert temp_db.mark_stale_not_seen_since("s", "2026-10-03T00:00:00Z", "2026-10-03") == 1
    assert _stale(temp_db, "1") == (1, "2026-10-02")


def test_mark_stale_without_stale_on_leaves_null(temp_db):
    temp_db.upsert(_p("1"), "2026-10-01T00:00:00Z")
    assert temp_db.mark_stale_not_seen_since("s", "2026-10-02T00:00:00Z") == 1
    assert _stale(temp_db, "1") == (1, None)


def test_list_newly_stale(temp_db):
    run = "2026-10-05T00:00:00Z"
    temp_db.upsert(_p("seen", title="Seen"), "2026-10-05T01:00:00Z")
    temp_db.upsert(_p("already", title="Already"), "2026-10-01T00:00:00Z")
    temp_db.set_stale_state("s", "already", 1, "2026-10-02")
    temp_db.upsert(_p("dup", title="Dup"), "2026-10-01T00:00:00Z")
    temp_db.set_duplicate_of("s", "dup", 1)
    temp_db.upsert(_p("unseen", title="Unseen"), "2026-10-01T00:00:00Z")
    temp_db.upsert(_p("other", site="o"), "2026-10-01T00:00:00Z")
    assert temp_db.list_newly_stale("s", run) == [("unseen", "Unseen")]


def test_list_stale_state_and_setters(temp_db):
    temp_db.upsert(_p("b", title="B"), "2026-10-01T00:00:00Z")
    temp_db.upsert(_p("a", title="A"), "2026-10-01T00:00:00Z")
    temp_db.upsert(_p("d", title="D"), "2026-10-01T00:00:00Z")
    temp_db.set_duplicate_of("s", "d", 1)
    temp_db.set_stale_state("s", "a", 1, "2026-10-02")
    assert temp_db.list_stale_state() == [
        ("s", "a", "A", 1, "2026-10-02"), ("s", "b", "B", 0, None)]
    temp_db.set_stale_since("s", "a", "2026-09-01")
    assert _stale(temp_db, "a") == (1, "2026-09-01")
    temp_db.set_stale_since("s", "a", None)
    assert _stale(temp_db, "a") == (1, None)


def test_find_duplicate_excludes_own_row(temp_db):
    a = JobPosting(site_id="s1", listing_id="a", source_url="u1", title="Dev",
                   client="Acme", location="Remote", description="d")
    b = JobPosting(site_id="s2", listing_id="b", source_url="u2", title="Dev",
                   client="Acme", location="Remote", description="d")
    temp_db.upsert(a, "2026-10-01T00:00:00Z")
    assert temp_db.find_duplicate("dev", "acme", "remote", "s1", "a") is None
    a_id = temp_db.conn.execute("SELECT id FROM jobs").fetchone()[0]
    assert temp_db.find_duplicate("dev", "acme", "remote", "s2", "b") == a_id


def test_migration_clears_self_duplicates(tmp_path):
    path = str(tmp_path / "dup.db")
    repo = JobRepository(path)
    for i in range(1, 5):
        repo.conn.execute(
            "INSERT INTO jobs (id, site_id, listing_id, source_url, title, content_hash,"
            " first_seen_at, last_seen_at, duplicate_of) VALUES (?, 's', ?, 'u', 'T', 'h',"
            " 'a', 'b', ?)", (i, str(i), 1 if i == 4 else i))
    repo.conn.commit()
    repo.conn.close()
    for _ in range(2):
        repo = JobRepository(path)
        rows = repo.conn.execute("SELECT id, duplicate_of FROM jobs ORDER BY id").fetchall()
        assert rows == [(1, None), (2, None), (3, None), (4, 1)]
        repo.conn.close()


def test_touch_seen_updates_single_row(temp_db):
    temp_db.upsert(_p("1", title="Row1"), "2026-10-01T00:00:00Z")
    temp_db.upsert(_p("2", title="Row2"), "2026-10-01T00:00:00Z")

    result = temp_db.touch_seen("s", ["1"], "2026-10-05T12:00:00Z")
    assert result == 1

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT last_seen_at FROM jobs WHERE listing_id = ?", ("1",))
    row1_time = cursor.fetchone()[0]
    assert row1_time == "2026-10-05T12:00:00Z"

    cursor.execute("SELECT last_seen_at FROM jobs WHERE listing_id = ?", ("2",))
    row2_time = cursor.fetchone()[0]
    assert row2_time == "2026-10-01T00:00:00Z"


def test_touch_seen_stale_row_stays_stale(temp_db):
    temp_db.upsert(_p("1"), "2026-10-01T00:00:00Z")
    temp_db.set_stale_state("s", "1", 1, "2026-10-02")

    result = temp_db.touch_seen("s", ["1"], "2026-10-05T12:00:00Z")
    assert result == 1

    assert _stale(temp_db, "1") == (1, "2026-10-02")

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT last_seen_at FROM jobs WHERE listing_id = ?", ("1",))
    row_time = cursor.fetchone()[0]
    assert row_time == "2026-10-05T12:00:00Z"


def test_touch_seen_unknown_ids(temp_db):
    temp_db.upsert(_p("1"), "2026-10-01T00:00:00Z")

    result = temp_db.touch_seen("s", ["unknown"], "2026-10-05T12:00:00Z")
    assert result == 0


def test_touch_seen_empty_list(temp_db):
    temp_db.upsert(_p("1"), "2026-10-01T00:00:00Z")

    result = temp_db.touch_seen("s", [], "2026-10-05T12:00:00Z")
    assert result == 0

    cursor = temp_db.conn.cursor()
    cursor.execute("SELECT last_seen_at FROM jobs WHERE listing_id = ?", ("1",))
    row_time = cursor.fetchone()[0]
    assert row_time == "2026-10-01T00:00:00Z"


def test_touch_seen_prevents_stale_marking(temp_db):
    run_start = "2026-10-05T00:00:00Z"
    temp_db.upsert(_p("1", title="Old"), "2026-10-01T00:00:00Z")
    temp_db.upsert(_p("2", title="Also old"), "2026-10-01T00:00:00Z")

    temp_db.touch_seen("s", ["1"], "2026-10-05T12:00:00Z")

    newly_stale = temp_db.list_newly_stale("s", run_start)
    assert newly_stale == [("2", "Also old")]
