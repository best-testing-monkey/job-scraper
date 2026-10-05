import json
import sys
from typing import Any, Iterator
from bs4 import BeautifulSoup

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.markdown_export import slugify
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class WorkingNomadsAdapter(SiteAdapter):
    site_id: str = "working_nomads"
    base_url: str = "https://www.workingnomads.com"
    screenshot_selector = "div.jd-desktop div.jd-description"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    listing_paths = ("/jobs",)
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
            source_url=self._human_url(page, title, client, stub.listing_id),
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

    def _human_url(self, page: Any, title: str, client: str, listing_id: str) -> str:
        canonical = self._canonical(page)
        if canonical:
            return canonical
        base = f"{slugify(title)}-{slugify(client)}"
        return self._resolve_human_url(base, listing_id)

    def _canonical(self, page: Any) -> str | None:
        if not page:
            return None
        link = BeautifulSoup(page, "html.parser").find("link", rel="canonical")
        href = link.get("href", "") if link else ""
        if isinstance(href, str) and href.startswith(f"{self.base_url}/jobs/"):
            return href
        return None

    def _resolve_human_url(self, base: str, listing_id: str) -> str:
        candidates = [
            f"{self.base_url}/jobs/{base}",
            f"{self.base_url}/jobs/{base}-{listing_id}",
        ]
        # fetch_page exposes only the body, not the final URL. The wrong slug
        # silently redirects to the /jobs index, so a candidate is valid only
        # if the page it serves declares that candidate as its canonical URL.
        for candidate in candidates:
            try:
                page = fetch_page(self.fetch_strategy, candidate)
            except Exception:
                break
            if (self._canonical(page) or "").rstrip("/") == candidate:
                return candidate
        print(
            f"working_nomads: could not verify human URL for {listing_id}",
            file=sys.stderr,
        )
        return candidates[1]

    def _extract_listing_id(self, url: str) -> str | None:
        if "/job/go/" in url:
            parts = url.split("/job/go/")
            if len(parts) == 2:
                job_id = parts[1].rstrip("/")
                return job_id
        return None
