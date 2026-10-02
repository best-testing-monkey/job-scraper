import json
import re
from typing import Any, Iterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class GuruAdapter(SiteAdapter):
    site_id: str = "guru"
    base_url: str = "https://www.guru.com"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    LISTING_URL: str = "https://www.guru.com/d/jobs/"

    def list_postings(self) -> Iterator[ListingStub]:
        current_url = self.LISTING_URL
        while current_url:
            page = fetch_page(self.fetch_strategy, current_url)
            soup = BeautifulSoup(page, "html.parser")
            cards = soup.find_all("div", class_="record jobRecord")
            for card in cards:
                # Extract listing_id from data-gid attribute
                listing_id = card.get("data-gid")
                if not listing_id:
                    continue

                # Extract title and detail URL from h2.jobRecord__title a
                title_elem = card.find("h2", class_="jobRecord__title")
                if not title_elem:
                    continue
                link = title_elem.find("a")
                if not link:
                    continue

                title = link.get_text(strip=True)
                detail_url = link.get("href", "")
                if not detail_url:
                    continue

                # Strip everything from &SearchUrl onward
                if "&SearchUrl" in detail_url:
                    detail_url = detail_url.split("&SearchUrl")[0]

                # Join relative URL with base URL if needed
                if detail_url.startswith("/"):
                    detail_url = self.base_url + detail_url

                yield ListingStub(
                    listing_id=listing_id,
                    detail_url=detail_url,
                    title=title,
                )

            # Look for next page link
            pagination = soup.find("ul", id="ctl00_guB_ulpaginate")
            next_url = None
            if pagination:
                # Find the next page link (look for link with text ">")
                links = pagination.find_all("a")
                for link in links:
                    if link.get_text(strip=True) == ">":
                        next_href = link.get("href")
                        if next_href:
                            next_url = urljoin(self.base_url, next_href)
                        break

            current_url = next_url

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract title
        title_elem = soup.find("h1", class_="jobHeading__title")
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract rate from jobHeading__budget
        rate = None
        budget_elem = soup.find("div", class_="jobHeading__budget")
        if budget_elem:
            rate = budget_elem.get_text(strip=True)

        # Extract posted_date and listing_id from jobHeading__meta
        posted_date = None
        meta_elem = soup.find("p", class_="jobHeading__meta")
        if meta_elem:
            meta_text = meta_elem.get_text()
            # Extract posted date - look for "Posted ... Days Ago" pattern
            match = re.search(r"Posted\s+([^|]+)", meta_text)
            if match:
                posted_date = match.group(1).strip()

        # Extract category from jobDetails__category p
        category = None
        category_elem = soup.find("div", class_="jobDetails__category")
        if category_elem:
            # Find the p tag within the category div
            p_elem = category_elem.find("p")
            if p_elem:
                # Extract the two-level category text
                # Format: <strong>Category1</strong> ... Category2
                strong_elem = p_elem.find("strong")
                category_parts = []
                if strong_elem:
                    category_parts.append(strong_elem.get_text(strip=True))
                # Get text after the SVG icon (which is the second category)
                # Split the p text by strong text to get the remaining text
                p_text = p_elem.get_text()
                if strong_elem:
                    strong_text = strong_elem.get_text(strip=True)
                    # Find the text after the strong tag and SVG
                    remaining = p_text.split(strong_text)[-1].strip()
                    if remaining:
                        category_parts.append(remaining)
                category = " > ".join(category_parts) if category_parts else None

        # Extract skills and join into extra_fields
        skills = []
        skill_elems = soup.find_all("a", class_="skillsList__skill")
        for skill_elem in skill_elems:
            skill_text = skill_elem.get_text(strip=True)
            if skill_text:
                skills.append(skill_text)

        # Extract description from pre.jobDetails__description
        description = ""
        desc_elem = soup.find("pre", class_="jobDetails__description")
        if desc_elem:
            description = desc_elem.get_text()
            # Strip the trailing "... <a href='/login.aspx?...'>Show more</a>" boilerplate
            # Look for the pattern and remove everything from "..." onward
            if " ... " in description:
                description = description.split(" ... ")[0].strip()

        # Extract location and jobLocationType from JSON-LD
        location = self._extract_location_from_json_ld(soup)
        job_location_type = self._extract_job_location_type_from_json_ld(soup)
        workplace_signal = self._map_job_location_type(job_location_type)
        workplace = classify_workplace(location, workplace_signal)

        # Build JobPosting
        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            rate=rate,
            posted_date=posted_date,
            category=category,
            description=description,
            client=None,
            location=location,
            workplace=workplace,
            hours=None,
            duration=None,
            extra_fields={"skills": ", ".join(skills)} if skills else {},
        )

        return posting

    def _extract_location_from_json_ld(self, soup: BeautifulSoup) -> str | None:
        """Extract location from JSON-LD applicantLocationRequirements."""
        json_ld = self._get_json_ld(soup)
        if not json_ld:
            return None
        location_req = json_ld.get("applicantLocationRequirements", {})
        if isinstance(location_req, dict):
            names = location_req.get("name", [])
            if isinstance(names, list) and names:
                return ", ".join(names)
        return None

    def _extract_job_location_type_from_json_ld(self, soup: BeautifulSoup) -> str | None:
        """Extract jobLocationType from JSON-LD (e.g., TELECOMMUTE, ON_SITE)."""
        json_ld = self._get_json_ld(soup)
        if not json_ld:
            return None
        return json_ld.get("jobLocationType")

    def _get_json_ld(self, soup: BeautifulSoup) -> dict | None:
        """Parse JSON-LD structured data from the page."""
        script = soup.find("script", type="application/ld+json")
        if not script:
            return None
        try:
            return json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            return None

    def _map_job_location_type(self, job_location_type: str | None) -> str | None:
        """Map guru's jobLocationType values to workplace classification text."""
        if not job_location_type:
            return None
        # Map common values: TELECOMMUTE -> Remote, ON_SITE -> On-site, HYBRID -> Hybrid
        type_upper = job_location_type.upper()
        if type_upper in ("TELECOMMUTE", "REMOTE"):
            return "Remote"
        if type_upper in ("ON_SITE", "ONSITE"):
            return "On-site"
        if type_upper == "HYBRID":
            return "Hybrid"
        return None
