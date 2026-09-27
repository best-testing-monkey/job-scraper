import re
from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import FetchStrategy, SiteAdapter


class FlexValueAdapter(SiteAdapter):
    site_id = "flexvalue"
    base_url = "https://aanvragen.flexvalue.nl"
    fetch_strategy = FetchStrategy.STATIC

    def list_postings(self) -> Iterator[ListingStub]:
        soup = BeautifulSoup(self.page, "html.parser")
        for anchor in soup.select("div.jobs-table div.grid-table a.table-row"):
            href = anchor.get("href", "")
            title_cell = anchor.select_one("div.data-cell.title-cell")
            if not href or not title_cell:
                continue

            title = title_cell.get_text(strip=True)

            match = re.search(r"/jobs/(\d+)-", href)
            if not match:
                continue

            listing_id = match.group(1)
            detail_url = self.base_url + href if href.startswith("/") else href

            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        title = ""
        title_elem = soup.select_one("main#job div.job-header h1")
        if title_elem:
            title = title_elem.get_text(strip=True)

        location = ""
        location_elem = soup.select_one("main#job div.job-header ul.job-tags li")
        if location_elem:
            location = location_elem.get_text(strip=True)

        job_description = soup.select_one("main#job div.job-description")

        hours = None
        duration = None
        extra_fields = {}
        client = None

        if job_description:
            table = job_description.find("table")
            if table:
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 2:
                        label_elem = tds[0].find("b")
                        label = label_elem.get_text(strip=True) if label_elem else ""
                        value = tds[1].get_text(strip=True)

                        if label == "Uren per week":
                            hours = value
                        elif label == "Start":
                            start_date = value
                        elif label == "Einddatum":
                            end_date = value
                        elif label in ["Optie op verlenging", "Deadline"]:
                            extra_fields[label] = value
                        elif label == "Locatie":
                            extra_fields["Locatie (detail)"] = value

            if "start_date" in locals() and "end_date" in locals():
                duration = f"{start_date} - {end_date}"

            description_text = self._extract_description(job_description)

            client = self._extract_client(job_description)

        return JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=None,
            location=location,
            hours=hours,
            duration=duration,
            description=description_text,
            extra_fields=extra_fields,
        )

    def _extract_description(self, job_description: Any) -> str:
        table = job_description.find("table")
        text_parts = []

        for elem in job_description.children:
            if isinstance(elem, str):
                text = elem.strip()
                if text:
                    text_parts.append(text)
            elif elem.name == "table":
                continue
            elif elem.name in ["b", "strong", "br", "span", "i"]:
                text = elem.get_text(strip=True)
                if text:
                    text_parts.append(text)

        full_text = " ".join(text_parts)
        full_text = re.sub(r"\s+", " ", full_text)
        return full_text.strip()

    def _extract_client(self, job_description: Any) -> str | None:
        text = job_description.get_text()

        match = re.search(r"opdrachtgever\s+(\S.*?)(?:\s+zijn|$)", text, re.IGNORECASE)
        if match:
            client_text = match.group(1).strip()

            for b_tag in job_description.find_all("b"):
                if b_tag.get_text(strip=True) in client_text:
                    return b_tag.get_text(strip=True)

        for b_tag in job_description.find_all("b"):
            b_text = b_tag.get_text(strip=True)
            if b_text and not b_text.isupper() and len(b_text) > 2:
                before_text = b_tag.previous_sibling
                if before_text and isinstance(before_text, str):
                    if "opdrachtgever" in before_text.lower():
                        return b_text

        return None
