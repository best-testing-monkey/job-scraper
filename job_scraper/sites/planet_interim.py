import re
from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class PlanetInterimAdapter(SiteAdapter):
    site_id: str = "planet_interim"
    base_url: str = "https://planetinterim.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    LISTING_URL: str = "https://planetinterim.nl/vind-interim-opdrachten"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(page, "html.parser")
        cards = soup.find_all("article", class_="pi-card")
        for card in cards:
            link_elem = card.find("a", class_="stretched-link")
            if not link_elem:
                continue
            title = link_elem.get_text(strip=True)
            detail_url = link_elem.get("href", "")
            if not detail_url:
                continue
            match = re.search(r"/(\d+)/", detail_url)
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

        title_elem = soup.find("h1", class_="pi-title")
        title = title_elem.get_text(strip=True) if title_elem else stub.title

        meta_dict = self._extract_meta_dict(soup)

        location = meta_dict.get("Standplaats")
        duration = meta_dict.get("Duur opdracht")
        rate = meta_dict.get("Indicatie uurtarief")
        hours = meta_dict.get("Aantal uren per week")
        posted_date = meta_dict.get("Laatste update")

        client = meta_dict.get("Opdrachtgever")
        if client and self._is_login_gate(client):
            client = None

        category_elem = soup.select_one(".pi-job-group-row .tag-pill span")
        category = category_elem.get_text(strip=True) if category_elem else None

        job_posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
            hours=hours,
            rate=rate,
            duration=duration,
            posted_date=posted_date,
            description="",
            scrape_note="Client name and job description require Planet Interim membership/login — not scraped.",
        )

        return job_posting

    def _extract_meta_dict(self, soup: BeautifulSoup) -> dict[str, str | None]:
        result = {}
        rows = soup.find_all("div", class_="pi-meta-row")
        for row in rows:
            label_elem = row.find("span", class_="pi-meta-label")
            value_elem = row.find("span", class_="pi-meta-value")
            if not label_elem or not value_elem:
                continue
            label = label_elem.get_text(strip=True).rstrip(":")
            value = value_elem.get_text(strip=True)
            result[label] = value if value else None
        return result

    def _is_login_gate(self, value: str) -> bool:
        return "log in" in value.lower() or "lid" in value.lower()
