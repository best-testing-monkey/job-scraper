import json
import re
import sqlite3
from job_scraper.core.models import JobPosting


class JobRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                site_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                client TEXT, category TEXT, level TEXT, status TEXT,
                location TEXT, hours TEXT, rate TEXT, duration TEXT,
                posted_date TEXT, experience TEXT, skills TEXT,
                description TEXT, scrape_note TEXT,
                extra_fields TEXT,
                content_hash TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                is_stale INTEGER NOT NULL DEFAULT 0,
                duplicate_of INTEGER REFERENCES jobs(id),
                UNIQUE(site_id, listing_id)
            )
        """)
        self.conn.commit()

    def upsert(self, posting: JobPosting, seen_at: str) -> bool:
        """Insert or update the row for (posting.site_id, posting.listing_id).
        Returns True if this was a new row OR content_hash changed;
        False if nothing about the content changed."""
        cursor = self.conn.cursor()
        content_hash = posting.content_hash()

        cursor.execute(
            "SELECT id, content_hash FROM jobs WHERE site_id = ? AND listing_id = ?",
            (posting.site_id, posting.listing_id),
        )
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                """
                INSERT INTO jobs (
                    site_id, listing_id, source_url, title, client, category,
                    level, status, location, hours, rate, duration,
                    posted_date, experience, skills, description, scrape_note,
                    extra_fields, content_hash, first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    posting.site_id,
                    posting.listing_id,
                    posting.source_url,
                    posting.title,
                    posting.client,
                    posting.category,
                    posting.level,
                    posting.status,
                    posting.location,
                    posting.hours,
                    posting.rate,
                    posting.duration,
                    posting.posted_date,
                    posting.experience,
                    json.dumps(posting.skills),
                    posting.description,
                    posting.scrape_note,
                    json.dumps(posting.extra_fields),
                    content_hash,
                    seen_at,
                    seen_at,
                ),
            )
            self.conn.commit()
            return True

        existing_id, existing_hash = row
        if content_hash != existing_hash:
            cursor.execute(
                """
                UPDATE jobs
                SET source_url = ?, title = ?, client = ?, category = ?,
                    level = ?, status = ?, location = ?, hours = ?, rate = ?,
                    duration = ?, posted_date = ?, experience = ?, skills = ?,
                    description = ?, scrape_note = ?, extra_fields = ?,
                    content_hash = ?, last_seen_at = ?, is_stale = 0
                WHERE site_id = ? AND listing_id = ?
                """,
                (
                    posting.source_url,
                    posting.title,
                    posting.client,
                    posting.category,
                    posting.level,
                    posting.status,
                    posting.location,
                    posting.hours,
                    posting.rate,
                    posting.duration,
                    posting.posted_date,
                    posting.experience,
                    json.dumps(posting.skills),
                    posting.description,
                    posting.scrape_note,
                    json.dumps(posting.extra_fields),
                    content_hash,
                    seen_at,
                    posting.site_id,
                    posting.listing_id,
                ),
            )
            self.conn.commit()
            return True

        cursor.execute(
            "UPDATE jobs SET last_seen_at = ?, is_stale = 0 WHERE id = ?",
            (seen_at, existing_id),
        )
        self.conn.commit()
        return False

    def mark_stale_not_seen_since(self, site_id: str, run_started_at: str) -> int:
        """Set is_stale=1 for every row of this site_id whose last_seen_at
        is earlier than run_started_at. Returns the number of rows updated."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE jobs SET is_stale = 1 WHERE site_id = ? AND last_seen_at < ?",
            (site_id, run_started_at),
        )
        self.conn.commit()
        return cursor.rowcount

    def find_duplicate(
        self, title: str, client: str | None, location: str | None
    ) -> int | None:
        """Case-insensitive, whitespace-normalized match against existing rows'
        (title, client, location). Returns the matching row's id, or None if no match.
        Rows that are themselves duplicates (duplicate_of IS NOT NULL) are not matched against."""
        cursor = self.conn.cursor()

        normalized_title = self._normalize_string(title)
        normalized_client = self._normalize_string(client) if client else None
        normalized_location = self._normalize_string(location) if location else None

        cursor.execute("SELECT id, title, client, location FROM jobs WHERE duplicate_of IS NULL")
        rows = cursor.fetchall()

        for row_id, row_title, row_client, row_location in rows:
            row_norm_title = self._normalize_string(row_title)
            row_norm_client = self._normalize_string(row_client) if row_client else None
            row_norm_location = self._normalize_string(row_location) if row_location else None

            if (
                row_norm_title == normalized_title
                and row_norm_client == normalized_client
                and row_norm_location == normalized_location
            ):
                return row_id

        return None

    def set_duplicate_of(self, site_id: str, listing_id: str, original_id: int) -> None:
        """Set duplicate_of on the row identified by (site_id, listing_id)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE jobs SET duplicate_of = ? WHERE site_id = ? AND listing_id = ?",
            (original_id, site_id, listing_id),
        )
        self.conn.commit()

    @staticmethod
    def _normalize_string(s: str | None) -> str | None:
        """Normalize a string: lowercase and collapse multiple spaces."""
        if s is None:
            return None
        s = s.lower()
        s = re.sub(r"\s+", " ", s).strip()
        return s
