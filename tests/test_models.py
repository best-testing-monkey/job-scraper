from job_scraper.core.models import JobPosting, ListingStub


def test_listing_stub_creation() -> None:
    stub = ListingStub(
        listing_id="123",
        detail_url="https://example.com/jobs/123",
        title="Software Engineer",
    )
    assert stub.listing_id == "123"
    assert stub.detail_url == "https://example.com/jobs/123"
    assert stub.title == "Software Engineer"


def test_job_posting_required_fields_only() -> None:
    posting = JobPosting(
        site_id="upwork",
        listing_id="job-123",
        source_url="https://upwork.com/jobs/123",
        title="Build a website",
    )
    assert posting.site_id == "upwork"
    assert posting.listing_id == "job-123"
    assert posting.source_url == "https://upwork.com/jobs/123"
    assert posting.title == "Build a website"
    assert posting.client is None
    assert posting.category is None
    assert posting.level is None
    assert posting.status is None
    assert posting.location is None
    assert posting.hours is None
    assert posting.rate is None
    assert posting.duration is None
    assert posting.posted_date is None
    assert posting.experience is None
    assert posting.skills == []
    assert posting.description == ""
    assert posting.scrape_note is None
    assert posting.extra_fields == {}


def test_job_posting_all_fields_populated() -> None:
    posting = JobPosting(
        site_id="upwork",
        listing_id="job-456",
        source_url="https://upwork.com/jobs/456",
        title="Mobile App Development",
        client="Acme Corp",
        category="Mobile Development",
        level="Intermediate",
        status="Open",
        location="Remote",
        hours="20-30 hours per week",
        rate="$50-75/hr",
        duration="2-3 months",
        posted_date="2024-01-15",
        experience="3+ years",
        skills=["iOS", "Swift", "Objective-C"],
        description="We need an iOS developer to build a mobile app.",
        scrape_note="Scraped successfully",
        extra_fields={"budget": "5000", "proposals": "42"},
    )
    assert posting.site_id == "upwork"
    assert posting.listing_id == "job-456"
    assert posting.source_url == "https://upwork.com/jobs/456"
    assert posting.title == "Mobile App Development"
    assert posting.client == "Acme Corp"
    assert posting.category == "Mobile Development"
    assert posting.level == "Intermediate"
    assert posting.status == "Open"
    assert posting.location == "Remote"
    assert posting.hours == "20-30 hours per week"
    assert posting.rate == "$50-75/hr"
    assert posting.duration == "2-3 months"
    assert posting.posted_date == "2024-01-15"
    assert posting.experience == "3+ years"
    assert posting.skills == ["iOS", "Swift", "Objective-C"]
    assert posting.description == "We need an iOS developer to build a mobile app."
    assert posting.scrape_note == "Scraped successfully"
    assert posting.extra_fields == {"budget": "5000", "proposals": "42"}


def test_content_hash_stable() -> None:
    posting1 = JobPosting(
        site_id="upwork",
        listing_id="job-789",
        source_url="https://upwork.com/jobs/789",
        title="Python Developer",
        client="Tech Startup",
        description="Looking for a Python expert.",
    )
    posting2 = JobPosting(
        site_id="fiverr",
        listing_id="different-id",
        source_url="https://fiverr.com/gigs/789",
        title="Python Developer",
        client="Tech Startup",
        description="Looking for a Python expert.",
    )
    assert posting1.content_hash() == posting2.content_hash()


def test_content_hash_changes_with_description() -> None:
    posting1 = JobPosting(
        site_id="upwork",
        listing_id="job-999",
        source_url="https://upwork.com/jobs/999",
        title="Frontend Developer",
        description="Need React expertise",
    )
    posting2 = JobPosting(
        site_id="upwork",
        listing_id="job-999",
        source_url="https://upwork.com/jobs/999",
        title="Frontend Developer",
        description="Need Vue expertise",
    )
    assert posting1.content_hash() != posting2.content_hash()
