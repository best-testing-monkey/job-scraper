import json
import re
from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class HarveyNashAdapter(SiteAdapter):
    site_id: str = "harveynash"
    base_url: str = "https://www.harveynash.nl"
    screenshot_selector = "div.post-content"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://www.harveynash.nl/sitemap.xml"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(page, "xml")

        # Find all <loc> elements
        locs = soup.find_all("loc")

        for loc in locs:
            url = loc.get_text(strip=True)

            # Match URLs of the form /vacatures/(\d+)-
            match = re.search(r"/vacatures/(\d+)-", url)
            if not match:
                continue

            listing_id = match.group(1)

            # Create a placeholder title from the URL slug
            # Extract the slug part after the digits
            slug_match = re.search(r"/vacatures/\d+-(.+?)/?$", url)
            title = slug_match.group(1).replace("-", " ") if slug_match else "Job Posting"

            yield ListingStub(
                listing_id=listing_id,
                detail_url=url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract __NEXT_DATA__ JSON
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

        try:
            data = json.loads(script_tag.string)
            page_data = data["props"]["pageProps"]["page"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

        title = page_data.get("title", stub.title)
        location = page_data.get("location")
        posted_date = page_data.get("published_at")
        description_html = page_data.get("description", "")

        # Extract workplace indicator from description
        workplace_signal = self._extract_workplace_signal(description_html)
        workplace = classify_workplace(location, workplace_signal)

        # Extract fields from categories
        categories_list = page_data.get("categories", [])
        categories_dict = {cat["name"]: cat["values"] for cat in categories_list}

        client = None
        if "Clients" in categories_dict and categories_dict["Clients"]:
            client = categories_dict["Clients"][0]["name"]

        category = None
        if "Functie categorie" in categories_dict and categories_dict["Functie categorie"]:
            category = ", ".join(v["name"] for v in categories_dict["Functie categorie"])

        hours = None
        if "Aantal uren" in categories_dict and categories_dict["Aantal uren"]:
            hours = categories_dict["Aantal uren"][0]["name"]

        employment_type = None
        if "Employment type" in categories_dict and categories_dict["Employment type"]:
            employment_type = categories_dict["Employment type"][0]["name"]

        # Handle rate: prefer salary_package if non-empty
        rate = page_data.get("salary_package")
        if not rate or rate == "":
            salary_low = page_data.get("salary_low")
            salary_high = page_data.get("salary_high")
            if salary_low and salary_high and (float(salary_low) > 0 or float(salary_high) > 0):
                rate = f"{salary_low}-{salary_high}"

        # Convert HTML description to Markdown
        description = html_to_markdown(description_html)

        extra_fields = {}
        if employment_type:
            extra_fields["employment_type"] = employment_type

        expires_at = page_data.get("expires_at")
        if expires_at:
            extra_fields["expires_at"] = expires_at

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
            workplace=workplace,
            hours=hours,
            rate=rate,
            posted_date=posted_date,
            description=description,
            extra_fields=extra_fields,
        )

        return posting

    def _extract_workplace_signal(self, description_html: str) -> str | None:
        """Extract workplace type signal from the HTML description.
        Looks for patterns like "Op locatie of vanuit huis: 50%-50%" indicating hybrid work."""
        if not description_html:
            return None

        # Extract text from HTML
        soup = BeautifulSoup(description_html, "html.parser")
        text = soup.get_text()

        # Look for percentage patterns like "50%-50%" or "50% - 50%"
        # which indicate hybrid/split work arrangement
        if re.search(r"\b50\s*%\s*-\s*50\s*%\b", text, re.IGNORECASE):
            return "Hybrid"

        return None
