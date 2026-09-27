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
