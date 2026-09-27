import re
from typing import Any, Iterator
from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import SiteAdapter, FetchStrategy


class ProActAdapter(SiteAdapter):
    site_id: str = "pro_act"
    base_url: str = "https://pro-act.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC

    def list_postings(self, page: Any) -> Iterator[ListingStub]:
        soup = BeautifulSoup(page, "html.parser")
        articles = soup.find_all("article", class_="vacancy-item")
        for article in articles:
            h3_tag = article.find("h3")
            if not h3_tag:
                continue
            link = h3_tag.find("a", class_="link-overlay")
            if not link:
                continue
            title = link.get_text(strip=True)
            detail_url = link.get("href", "")
            if not detail_url:
                continue
            match = re.search(r"-(\d+)/?$", detail_url)
            if not match:
                continue
            listing_id = match.group(1)
            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")
        title = self._extract_title(soup)
        posted_date, expiry_date = self._extract_dates(soup)
        hours = self._extract_hours(soup)
        client, location, rate = self._extract_general_info(soup)
        description = self._extract_description(soup)
        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            location=location,
            hours=hours,
            rate=rate,
            posted_date=posted_date,
            description=description,
            extra_fields={},
        )
        if expiry_date:
            posting.extra_fields["Verloopt"] = expiry_date
        return posting

    def _extract_title(self, soup: BeautifulSoup) -> str:
        section = soup.find("section", id="section-vacancy-info")
        if not section:
            return ""
        main_info = section.find("div", class_="main-info")
        if not main_info:
            return ""
        h1 = main_info.find("h1")
        if not h1:
            return ""
        return h1.get_text(strip=True)

    def _extract_dates(self, soup: BeautifulSoup) -> tuple[str | None, str | None]:
        section = soup.find("section", id="section-vacancy-info")
        if not section:
            return None, None
        date_span = section.find("span", class_="date")
        if not date_span:
            return None, None
        date_text = date_span.get_text(strip=True)
        parts = date_text.split("Verloopt:")
        posted_date = None
        expiry_date = None
        if len(parts) >= 1:
            posted_str = parts[0].replace("Geplaatst:", "").strip()
            if posted_str:
                posted_date = posted_str
        if len(parts) >= 2:
            expiry_str = parts[1].strip()
            if expiry_str:
                expiry_date = expiry_str
        return posted_date, expiry_date

    def _extract_hours(self, soup: BeautifulSoup) -> str | None:
        section = soup.find("section", id="section-vacancy-info")
        if not section:
            return None
        vacancy_meta = section.find("div", class_="vacancy-meta")
        if not vacancy_meta:
            return None
        name_divs = vacancy_meta.find_all("div", class_="name")
        for i, name_div in enumerate(name_divs):
            if "Uren per week" in name_div.get_text(strip=True):
                answer_divs = vacancy_meta.find_all("div", class_="answer")
                if i < len(answer_divs):
                    return answer_divs[i].get_text(strip=True)
        return None

    def _extract_general_info(
        self, soup: BeautifulSoup
    ) -> tuple[str | None, str | None, str | None]:
        client = None
        location = None
        rate = None
        section_content = soup.find("section", class_="section-content")
        if not section_content:
            return client, location, rate
        content_wrapper = section_content.find("div", class_="content-wrapper")
        if not content_wrapper:
            return client, location, rate
        p_tags = content_wrapper.find_all("p")
        for p_tag in p_tags:
            p_text = p_tag.get_text()
            client_match = re.search(
                r"eindklant (?:de |het )?([^.,]+)", p_text, re.IGNORECASE
            )
            if client_match:
                client = client_match.group(1).strip()
                break
        full_text = content_wrapper.get_text(separator=" ", strip=True)
        tarief_match = re.search(r"Tarief:\s*(\w+)", full_text)
        if tarief_match:
            rate = tarief_match.group(1).strip()
        locatie_match = re.search(r"Locatie:\s*(\w+)", full_text)
        if locatie_match:
            location = locatie_match.group(1).strip()
        return client, location, rate

    def _extract_description(self, soup: BeautifulSoup) -> str:
        section_content = soup.find("section", class_="section-content")
        if not section_content:
            return ""
        content_wrapper = section_content.find("div", class_="content-wrapper")
        if not content_wrapper:
            return ""
        description = content_wrapper.get_text(separator=" ", strip=True)
        description = re.sub(r"\s+", " ", description)
        return description
