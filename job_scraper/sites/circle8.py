import json
import re
from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class Circle8Adapter(SiteAdapter):
    site_id: str = "circle8"
    base_url: str = "https://www.circle8.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    LISTING_URL: str = "https://www.circle8.nl/opdrachten"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(page, "html.parser")
        cards = soup.find_all("a", class_="c-vacancy-grid-card")
        for card in cards:
            title_elem = card.find(class_="c-vacancy-grid-card__title")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            detail_url = card.get("href", "")
            if not detail_url:
                continue
            match = re.search(r"_([A-Za-z0-9-]+)$", detail_url)
            if not match:
                continue
            listing_id = match.group(1)
            detail_url = f"{self.base_url}{detail_url}"
            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")
        job_posting = self._extract_from_json_ld(soup)
        if not job_posting:
            job_posting = JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )
        else:
            job_posting.listing_id = stub.listing_id
            job_posting.source_url = stub.detail_url

        self._extract_usp_values(soup, job_posting)
        job_posting.scrape_note = (
            "Page 1 only — pagination requires JS interaction not yet supported"
        )
        return job_posting

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> JobPosting | None:
        script_tags = soup.find_all("script", type="application/ld+json")
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    title = data.get("title", "")
                    description = html_to_markdown(data.get("description", ""))
                    posted_date = data.get("datePosted")
                    location = (
                        data.get("jobLocation", {})
                        .get("address", {})
                        .get("addressLocality")
                    )
                    workplace = classify_workplace(location)
                    client = data.get("hiringOrganization", {}).get("name")
                    category = data.get("industry")
                    rate = None
                    base_salary = data.get("baseSalary", {})
                    if isinstance(base_salary, dict):
                        rate = base_salary.get("value")
                    if isinstance(rate, dict):
                        rate = None

                    posting = JobPosting(
                        site_id=self.site_id,
                        listing_id="",
                        source_url="",
                        title=title,
                        description=description,
                        posted_date=posted_date,
                        location=location,
                        workplace=workplace,
                        client=client,
                        category=category,
                        rate=rate,
                    )
                    valid_through = data.get("validThrough")
                    if valid_through:
                        posting.extra_fields["validThrough"] = valid_through
                    return posting
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def _extract_usp_values(self, soup: BeautifulSoup, posting: JobPosting) -> None:
        usp_divs = soup.select(
            ".c-vacancy-hero__usp-container .c-vacancy-hero__usp div:not(.c-vacancy-hero__usp-icon)"
        )
        if len(usp_divs) >= 5:
            duration_text = usp_divs[1].get_text(strip=True)
            hours_text = usp_divs[2].get_text(strip=True)
            posting.duration = duration_text
            posting.hours = hours_text
