import re
from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import FetchStrategy, SiteAdapter, fetch_page


class HeroAdapter(SiteAdapter):
    site_id = "hero"
    base_url = "https://hero.eu"
    fetch_strategy = FetchStrategy.STATIC
    LISTING_URL = "https://hero.eu/interim-opdrachten"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(page, "html.parser")
        ul = soup.find("ul", class_="divide-y")
        if not ul:
            return

        for li in ul.find_all("li", class_="py-3"):
            h5 = li.find("h5", class_="hero-h5")
            if not h5:
                continue
            a = h5.find("a")
            if not a:
                continue

            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not href:
                continue

            # Extract listing_id from URL
            match = re.search(r"-([0-9a-f]{8})$", href)
            if not match:
                continue
            listing_id = match.group(1)

            # Make absolute URL
            if href.startswith("/"):
                detail_url = f"{self.base_url}{href}"
            else:
                detail_url = href

            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract title from h1.hero-h2
        title = ""
        h1 = soup.find("h1", class_="hero-h2")
        if h1:
            # Get text and strip the decorative span
            title_text = h1.get_text()
            # Remove trailing decorative characters (the caret/pipe)
            title = title_text.replace("|", "").strip()

        # Extract metadata from li.hero-lead
        location = None
        hours = None

        metadata_ul = soup.find("ul", class_="mt-4")
        if metadata_ul:
            for li in metadata_ul.find_all("li", class_="hero-lead"):
                # Get all spans in the li
                spans = li.find_all("span")
                # The second span (index 1) contains the label: value
                if len(spans) >= 2:
                    label_value = spans[1].get_text()
                    # Split on ": "
                    if ": " in label_value:
                        label, value = label_value.split(": ", 1)
                        if label.strip() == "Regio":
                            location = value.strip()
                        elif label.strip() == "Uren per week":
                            hours = value.strip()

        # Extract description
        description = ""
        desc_div = soup.find("div", class_="hero-requisition-body")
        if desc_div:
            p = desc_div.find("p")
            if p:
                description = p.get_text(strip=True)

        return JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            location=location,
            hours=hours,
            description=description,
            category=None,
            posted_date=None,
            client=None,
            rate=None,
            duration=None,
        )
