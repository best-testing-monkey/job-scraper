from typing import Any, Iterator
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class ArcDevAdapter(SiteAdapter):
    site_id: str = "arc_dev"
    base_url: str = "https://arc.dev"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://arc.dev/remote-jobs/qa-engineer"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(page, "html.parser")
        job_cards = soup.find_all("div", {"data-testid": "job-card"})
        for card in job_cards:
            listing_id = card.get("data-job-random-key", "")
            if not listing_id:
                continue
            job_title_link = card.find("a", class_="job-title")
            if not job_title_link:
                continue
            title = job_title_link.get_text(strip=True)
            href = job_title_link.get("href", "")
            if not href:
                continue
            detail_url = urljoin(self.base_url, href)
            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")
        title = self._extract_title(soup)
        client = self._extract_client(soup)
        location = self._extract_location(soup)
        workplace = classify_workplace(location)
        rate = self._extract_rate(soup)
        category = self._extract_category(soup)
        seniority = self._extract_seniority(soup)
        visa = self._extract_visa(soup)
        duration, posted_date = self._extract_duration_and_posted_date(soup)
        description = self._extract_description(soup)

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
            workplace=workplace,
            rate=rate,
            duration=duration,
            posted_date=posted_date,
            description=description,
            extra_fields={},
        )
        if seniority:
            posting.extra_fields["seniority"] = seniority
        if visa:
            posting.extra_fields["visa"] = visa
        return posting

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.find("h1", class_="title")
        if not title_tag:
            return ""
        return title_tag.get_text(strip=True)

    def _extract_client(self, soup: BeautifulSoup) -> str | None:
        company_tag = soup.find("a", class_="company-name")
        if not company_tag:
            return None
        return company_tag.get_text(strip=True)

    def _extract_location(self, soup: BeautifulSoup) -> str | None:
        return self._extract_detail_by_label(soup, "Location")

    def _extract_rate(self, soup: BeautifulSoup) -> str | None:
        return self._extract_detail_by_label(soup, "Salary Estimate")

    def _extract_category(self, soup: BeautifulSoup) -> str | None:
        return self._extract_detail_by_label(soup, "Tech stacks")

    def _extract_seniority(self, soup: BeautifulSoup) -> str | None:
        return self._extract_detail_by_label(soup, "Seniority")

    def _extract_visa(self, soup: BeautifulSoup) -> str | None:
        return self._extract_detail_by_label(soup, "Visa")

    def _extract_detail_by_label(self, soup: BeautifulSoup, label_text: str) -> str | None:
        details = soup.find("div", class_="details")
        if not details:
            return None
        detail_divs = details.find_all("div", recursive=False)
        for detail_div in detail_divs:
            h3_tag = detail_div.find("h3")
            if not h3_tag:
                continue
            label_span = h3_tag.find("span", class_="title")
            if not label_span:
                continue
            current_label = label_span.get_text(strip=True)
            if current_label == label_text:
                value_div = detail_div.find("div", class_="value")
                if not value_div:
                    return None
                # For rate, extract from first span to avoid icon text
                if label_text == "Salary Estimate":
                    span = value_div.find("span")
                    if span:
                        return span.get_text(strip=True)
                    return None
                return value_div.get_text(strip=True)
        return None

    def _extract_duration_and_posted_date(self, soup: BeautifulSoup) -> tuple[str | None, str | None]:
        details = soup.find("div", class_="details")
        if not details:
            return None, None
        detail_divs = details.find_all("div", recursive=False)
        if not detail_divs:
            return None, None
        last_div = detail_divs[-1]
        value_div = last_div.find("div", class_="single-line")
        if not value_div:
            return None, None
        children = value_div.find_all("div", recursive=False)
        if len(children) < 2:
            return None, None
        duration = children[0].get_text(strip=True)
        posted_date = children[1].get_text(strip=True)
        return duration, posted_date

    def _extract_description(self, soup: BeautifulSoup) -> str:
        tab = soup.find("div", {"id": "tab-job-details"})
        if not tab:
            return ""
        return html_to_markdown(str(tab))
