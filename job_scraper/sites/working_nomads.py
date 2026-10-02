import json
from typing import Any, Iterator
from bs4 import BeautifulSoup

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class WorkingNomadsAdapter(SiteAdapter):
    site_id: str = "working_nomads"
    base_url: str = "https://www.workingnomads.com"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://www.workingnomads.com/api/exposed_jobs/"

    def __init__(self) -> None:
        self._job_cache: dict[str, dict[str, Any]] = {}

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        jobs = json.loads(page)
        for job in jobs:
            url = job.get("url", "")
            title = job.get("title", "")
            if not url:
                continue
            listing_id = self._extract_listing_id(url)
            if not listing_id:
                continue
            self._job_cache[listing_id] = job
            yield ListingStub(
                listing_id=listing_id,
                detail_url=url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        job = self._job_cache.get(stub.listing_id, {})
        title = job.get("title", "")
        client = job.get("company_name", "")
        tags = job.get("tags", "")
        location = job.get("location", "")
        posted_date = job.get("pub_date", "")
        description = html_to_markdown(job.get("description", ""))
        category_name = job.get("category_name", "")
        # Working Nomads is a remote-jobs-only board by definition (its
        # location field is a timezone constraint, e.g. "Time zone: CET
        # (+/- 3 hours)", never the literal word "remote"), so classify_
        # workplace(location) alone would misclassify every posting here
        # as unknown. Fall back to the site's own premise, but still
        # respect an explicit Hybrid/On-site signal if one ever appears.
        workplace = classify_workplace(location) or "Fully Remote"

        extra_fields: dict[str, str] = {}
        if category_name:
            extra_fields["category_name"] = category_name

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=tags,
            location=location,
            workplace=workplace,
            hours=None,
            rate=None,
            duration=None,
            posted_date=posted_date,
            description=description,
            extra_fields=extra_fields,
        )
        return posting

    def _extract_listing_id(self, url: str) -> str | None:
        if "/job/go/" in url:
            parts = url.split("/job/go/")
            if len(parts) == 2:
                job_id = parts[1].rstrip("/")
                return job_id
        return None
