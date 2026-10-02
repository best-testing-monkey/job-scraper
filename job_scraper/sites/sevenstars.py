import json
import re
from typing import Any, Iterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class SevenstarsAdapter(SiteAdapter):
    site_id: str = "sevenstars"
    base_url: str = "https://www.sevenstars.nl"
    screenshot_selector = "div.c-vacancy-paragraph__body-text.job-description"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    LISTING_URL: str = "https://www.sevenstars.nl/opdrachten"

    def list_postings(self) -> Iterator[ListingStub]:
        current_url = self.LISTING_URL
        while current_url:
            page = fetch_page(self.fetch_strategy, current_url)
            soup = BeautifulSoup(page, "html.parser")
            cards = soup.find_all("div", class_="c-vacancy-grid-card")
            for card in cards:
                header_left = card.find("div", class_="c-vacancy-grid-card__header--left")
                if not header_left:
                    continue
                link = header_left.find("a", href=re.compile(r"^/opdracht/"))
                if not link:
                    continue
                detail_url = link.get("href", "")
                if not detail_url:
                    continue

                # Extract title from h3 inside the link
                title_elem = link.find("h3", class_="c-vacancy-grid-card__title")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Join relative URL with base URL if needed
                if detail_url.startswith("/"):
                    detail_url = self.base_url + detail_url

                # Extract listing_id from href: /opdracht/agilecoach_7S-004982 -> 7S-004982
                match = re.search(r"_([A-Za-z0-9-]+)$", detail_url)
                if not match:
                    continue
                listing_id = match.group(1)

                yield ListingStub(
                    listing_id=listing_id,
                    detail_url=detail_url,
                    title=title,
                )

            # Look for next page link
            pagination_wrapper = soup.find("div", class_="c-lister-pagination__wrapper")
            next_url = None
            if pagination_wrapper:
                next_link = pagination_wrapper.find(
                    "a", class_="c-lister-pagination__page-control--next"
                )
                if next_link and next_link.get("data-disabled") == "false":
                    next_href = next_link.get("href")
                    if next_href:
                        next_url = urljoin(self.LISTING_URL, next_href)

            current_url = next_url

    def _extract_workplace_from_description(self, description: str) -> str | None:
        """Extract and normalize workplace type from job description.
        Looks for Dutch workplace keywords and normalizes them to English.
        Returns the normalized keyword (e.g. "Hybrid") or None if not found."""
        if not description:
            return None

        # Normalize Dutch workplace keywords to English for classify_workplace
        # Must be done before passing to classify_workplace since it only recognizes English
        normalized_keywords = {
            r"\bhybride\b": "Hybrid",
            r"\bhybride\s+werken\b": "Hybrid",
            r"\bthuis(?:werken|werk)\b": "Fully Remote",  # thuiswerken/thuiswerk
            r"\bvolledig\s+remote\b": "Fully Remote",
            r"\bwerken\s+vanuit\s+huis\b": "Fully Remote",
            r"\bdeels\s+thuiswerken\b": "Hybrid",
            r"\bop\s+locatie\b": "On-site",
        }

        description_lower = description.lower()
        for pattern, keyword in normalized_keywords.items():
            if re.search(pattern, description_lower, re.IGNORECASE):
                return keyword

        return None

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract from JSON-LD
        title = None
        description = None
        posted_date = None
        location = None
        rate = None

        script_tags = soup.find_all("script", {"type": "application/ld+json"})
        for script_tag in script_tags:
            try:
                data = json.loads(script_tag.string)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    title = data.get("title", "")

                    raw_description = data.get("description", "")
                    if raw_description:
                        description = html_to_markdown(raw_description)

                    posted_date = data.get("datePosted")

                    job_location = data.get("jobLocation", {})
                    if isinstance(job_location, dict):
                        address = job_location.get("address", {})
                        if isinstance(address, dict):
                            location = address.get("addressLocality")

                    base_salary = data.get("baseSalary", {})
                    if isinstance(base_salary, dict):
                        salary_value = base_salary.get("value", {})
                        if isinstance(salary_value, dict):
                            min_val = salary_value.get("MinValue", "")
                            max_val = salary_value.get("MaxValue", "")
                            if min_val and max_val:
                                rate = f"{min_val}-{max_val}"
                    break
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        # Extract hours and duration from USP values
        hours = None
        duration = None
        usp_values = soup.find_all("h5", class_="c-vacancy-hero__usp-value")
        if len(usp_values) >= 3:
            # Index 1 is duration
            duration = usp_values[1].get_text(strip=True)
            # Index 2 is hours
            hours = usp_values[2].get_text(strip=True)

        # Extract and classify workplace
        workplace_signal = self._extract_workplace_from_description(description)
        workplace = classify_workplace(location, workplace_signal)

        # Build JobPosting
        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title or "",
            location=location,
            workplace=workplace,
            hours=hours,
            duration=duration,
            rate=rate,
            posted_date=posted_date,
            description=description or "",
            client=None,
            category=None,
            extra_fields={},
        )

        if posted_date:
            posting.extra_fields["validThrough"] = data.get("validThrough", "")

        return posting
