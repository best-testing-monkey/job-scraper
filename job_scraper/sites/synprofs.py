import json
import re
from typing import Any, Iterator
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class SynprofsAdapter(SiteAdapter):
    site_id: str = "synprofs"
    base_url: str = "https://www.synprofs.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    screenshot_selector = "div.sd-sdcx-components-vacancies-parts-publication-text"
    screenshot_hide_selectors = ("header#masthead",)  # fixed site header overlaps top lines
    LISTING_URL: str = "https://www.synprofs.nl/vacancy-sitemap.xml"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        root = ET.fromstring(page)

        # Parse XML sitemap - namespace is required
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url_elem in root.findall("sm:url", ns):
            loc_elem = url_elem.find("sm:loc", ns)
            if loc_elem is None:
                continue

            url = loc_elem.text
            if not url:
                continue

            # Extract listing_id and slug from URL
            # Pattern: https://www.synprofs.nl/opdracht/<slug>-<id>/
            match = re.search(r"/opdracht/(.+?)-(\d+)/$", url)
            if not match:
                continue

            slug = match.group(1)
            listing_id = match.group(2)

            # Create placeholder title from slug (replace hyphens with spaces, title case)
            title = slug.replace("-", " ").title()

            yield ListingStub(
                listing_id=listing_id,
                detail_url=url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract JSON-LD data
        ld_json = self._extract_ld_json(soup)

        # Extract title
        title = ld_json.get("title", "")

        # Extract client from hiringOrganization
        client = None
        if "hiringOrganization" in ld_json:
            client = ld_json["hiringOrganization"].get("name")

        # Extract location from jobLocation
        location = None
        workplace_signal = None
        if "jobLocation" in ld_json:
            address = ld_json["jobLocation"].get("address", {})
            full_location = address.get("addressLocality")
            # Split location from workplace type (e.g., "Assen / hybride" → "Assen", "hybride")
            if full_location:
                parts = [p.strip() for p in full_location.split("/")]
                location = parts[0] if parts else None
                # Translate Dutch workplace keywords to English before classify_workplace
                if len(parts) > 1:
                    workplace_nl = parts[1].lower()
                    if "hybride" in workplace_nl:
                        workplace_signal = "Hybrid"
                    elif "remote" in workplace_nl or "thuiswerken" in workplace_nl or "volledig remote" in workplace_nl:
                        workplace_signal = "Fully Remote"
                    elif "op locatie" in workplace_nl or "ter plaatse" in workplace_nl:
                        workplace_signal = "On-site"
                    else:
                        workplace_signal = parts[1]  # Pass as-is to classify_workplace

        # Extract posted_date
        posted_date = ld_json.get("datePosted")

        # Classify workplace
        workplace = classify_workplace(location, workplace_signal)

        # Extract validThrough for extra_fields
        valid_through = ld_json.get("validThrough")

        # Cross-check identifier
        identifier = ld_json.get("identifier", {})
        if isinstance(identifier, dict):
            ld_id = identifier.get("value")
            if ld_id and str(ld_id) != stub.listing_id:
                pass  # Mismatch, but we don't fail - use stub's ID

        # Extract hours and duration from the spec list
        hours, duration = self._extract_hours_and_duration(soup)

        # Extract description
        description = self._extract_description(soup)

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            location=location,
            workplace=workplace,
            hours=hours,
            duration=duration,
            posted_date=posted_date,
            description=description,
            category=None,
            rate=None,
            extra_fields={},
        )

        if valid_through:
            posting.extra_fields["validThrough"] = valid_through

        return posting

    def _extract_ld_json(self, soup: BeautifulSoup) -> dict[str, Any]:
        # Find all JSON-LD scripts and look for JobPosting
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            if not script.string:
                continue

            try:
                data = json.loads(script.string)

                # Check if this is a JobPosting or contains one
                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        return data
                    elif "@graph" in data:
                        # Check if @graph contains JobPosting
                        for item in data.get("@graph", []):
                            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                                return item
            except json.JSONDecodeError:
                continue

        return {}

    def _extract_hours_and_duration(self, soup: BeautifulSoup) -> tuple[str | None, str | None]:
        hours = None
        duration = None

        # Find the ul.publication-text-vacancy-specs
        spec_ul = soup.find("ul", class_="publication-text-vacancy-specs")
        if not spec_ul:
            return hours, duration

        # Get all li items
        items = spec_ul.find_all("li")

        # Items are: hours, location, start date, duration, deadline
        # We want hours and duration
        if len(items) > 0:
            # First item is hours (e.g., "36 uur")
            hours_text = items[0].get_text(strip=True)
            if hours_text:
                hours = hours_text

        if len(items) > 3:
            # Fourth item is duration (e.g., "12 maanden")
            duration_text = items[3].get_text(strip=True)
            if duration_text:
                duration = duration_text

        return hours, duration

    def _extract_description(self, soup: BeautifulSoup) -> str:
        description_parts = []

        # List of container classes to extract in order
        containers = [
            "publication-text-introInformation",
            "publication-text-companyInformation",
            "publication-text-vacancyInformation",
            "publication-text-requirementsInformation",
            "publication-text-offerInformation",
        ]

        for container_class in containers:
            container = soup.find("div", class_=container_class)
            if not container:
                continue

            # Convert each container separately to preserve formatting
            text = html_to_markdown(str(container))
            if text:
                description_parts.append(text)

        # Join all parts with blank lines
        description = "\n\n".join(description_parts)

        return description
