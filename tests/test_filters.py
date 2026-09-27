import pytest
from job_scraper.core.filters import is_excluded, apply_dedup
from job_scraper.core.models import JobPosting
from job_scraper.core.db import JobRepository


class TestIsExcluded:
    def test_excluded_geen_zzp_case_insensitive(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="1",
            source_url="http://test.com",
            title="Test",
            description="Let op: geen ZZP'ers",
        )
        assert is_excluded(posting) is True

    def test_excluded_zzp_niet_toegestaan(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="2",
            source_url="http://test.com",
            title="Test",
            description="zzp niet toegestaan",
        )
        assert is_excluded(posting) is True

    def test_excluded_enkel_detachering(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="3",
            source_url="http://test.com",
            title="Test",
            description="enkel detachering",
        )
        assert is_excluded(posting) is True

    def test_excluded_in_loondienst(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="4",
            source_url="http://test.com",
            title="Test",
            description="in loondienst",
        )
        assert is_excluded(posting) is True

    def test_not_excluded_no_keywords(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="5",
            source_url="http://test.com",
            title="Test",
            description="This is a great job opportunity for freelancers",
        )
        assert is_excluded(posting) is False

    def test_excluded_mixed_case(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="6",
            source_url="http://test.com",
            title="Test",
            description="GEEN ZZP is mentioned here",
        )
        assert is_excluded(posting) is True

    def test_excluded_keyword_in_longer_text(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="7",
            source_url="http://test.com",
            title="Test",
            description="We are looking for candidates but unfortunately in loondienst only",
        )
        assert is_excluded(posting) is True


class TestApplyDedup:
    def test_apply_dedup_finds_existing_match(self, tmp_path) -> None:
        db_path = str(tmp_path / "test.db")
        repo = JobRepository(db_path)

        existing_posting = JobPosting(
            site_id="site1",
            listing_id="existing1",
            source_url="http://test.com/1",
            title="Senior Tester",
            client="Acme BV",
            location="Den Haag",
            description="Test job",
        )
        repo.upsert(existing_posting, "2025-01-01T00:00:00Z")

        new_posting = JobPosting(
            site_id="site2",
            listing_id="new1",
            source_url="http://test.com/2",
            title="  SENIOR   tester ",
            client="acme bv",
            location="den haag",
            description="Another test job",
        )

        result_posting, duplicate_id = apply_dedup(new_posting, repo)

        assert result_posting is new_posting
        assert duplicate_id is not None
        assert duplicate_id == 1

    def test_apply_dedup_no_match(self, tmp_path) -> None:
        db_path = str(tmp_path / "test.db")
        repo = JobRepository(db_path)

        existing_posting = JobPosting(
            site_id="site1",
            listing_id="existing1",
            source_url="http://test.com/1",
            title="Senior Tester",
            client="Acme BV",
            location="Den Haag",
            description="Test job",
        )
        repo.upsert(existing_posting, "2025-01-01T00:00:00Z")

        new_posting = JobPosting(
            site_id="site2",
            listing_id="new1",
            source_url="http://test.com/2",
            title="Junior Developer",
            client="Different Company",
            location="Amsterdam",
            description="A different job",
        )

        result_posting, duplicate_id = apply_dedup(new_posting, repo)

        assert result_posting is new_posting
        assert duplicate_id is None

    def test_apply_dedup_empty_database(self, tmp_path) -> None:
        db_path = str(tmp_path / "test.db")
        repo = JobRepository(db_path)

        posting = JobPosting(
            site_id="site1",
            listing_id="new1",
            source_url="http://test.com/1",
            title="Senior Tester",
            client="Acme BV",
            location="Den Haag",
            description="Test job",
        )

        result_posting, duplicate_id = apply_dedup(posting, repo)

        assert result_posting is posting
        assert duplicate_id is None

    def test_apply_dedup_whitespace_normalization(self, tmp_path) -> None:
        db_path = str(tmp_path / "test.db")
        repo = JobRepository(db_path)

        existing_posting = JobPosting(
            site_id="site1",
            listing_id="existing1",
            source_url="http://test.com/1",
            title="Test    Job",
            client="Company  Name",
            location="City",
            description="Test job",
        )
        repo.upsert(existing_posting, "2025-01-01T00:00:00Z")

        new_posting = JobPosting(
            site_id="site2",
            listing_id="new1",
            source_url="http://test.com/2",
            title="   test   job   ",
            client="   company   name   ",
            location="   city   ",
            description="Another test job",
        )

        result_posting, duplicate_id = apply_dedup(new_posting, repo)

        assert duplicate_id is not None
        assert duplicate_id == 1

    def test_apply_dedup_null_client_location(self, tmp_path) -> None:
        db_path = str(tmp_path / "test.db")
        repo = JobRepository(db_path)

        existing_posting = JobPosting(
            site_id="site1",
            listing_id="existing1",
            source_url="http://test.com/1",
            title="Senior Tester",
            client=None,
            location=None,
            description="Test job",
        )
        repo.upsert(existing_posting, "2025-01-01T00:00:00Z")

        new_posting = JobPosting(
            site_id="site2",
            listing_id="new1",
            source_url="http://test.com/2",
            title="  SENIOR   tester ",
            client=None,
            location=None,
            description="Another test job",
        )

        result_posting, duplicate_id = apply_dedup(new_posting, repo)

        assert duplicate_id is not None
        assert duplicate_id == 1

    def test_apply_dedup_returns_original_posting(self, tmp_path) -> None:
        db_path = str(tmp_path / "test.db")
        repo = JobRepository(db_path)

        posting = JobPosting(
            site_id="site1",
            listing_id="new1",
            source_url="http://test.com/1",
            title="Senior Tester",
            client="Acme BV",
            location="Den Haag",
            description="Test job",
        )

        result_posting, _ = apply_dedup(posting, repo)

        assert result_posting is posting
