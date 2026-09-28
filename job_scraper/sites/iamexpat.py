import re
from typing import Any, Iterator
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class IamexpatAdapter(SiteAdapter):
    site_id: str = "iamexpat"
    base_url: str = "https://www.iamexpat.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://www.iamexpat.nl/career/jobs-netherlands"

    def list_postings(self) -> Iterator[ListingStub]:
        page_num = 1
        while True:
            url = f"{self.LISTING_URL}?page={page_num}"
            page = fetch_page(self.fetch_strategy, url)
            soup = BeautifulSoup(page, "html.parser")

            # Find all job cards using substring match on class
            cards = soup.find_all("a", class_=re.compile(r"JobBoardItemCard_cardWrapper"))

            if not cards:
                # No cards on this page, we're done
                break

            for card in cards:
                href = card.get("href", "")
                if not href:
                    continue

                # Extract title from span.title-7
                title_elem = card.find("span", class_="title-7")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Make URL absolute if it's relative
                if href.startswith("/"):
                    detail_url = urljoin(self.base_url, href)
                else:
                    detail_url = href

                # Extract listing_id from the trailing path segment
                # e.g., /career/jobs-netherlands/.../jfkJ1hM6ah4rhhDYWfLNS1 -> jfkJ1hM6ah4rhhDYWfLNS1
                path_parts = detail_url.rstrip("/").split("/")
                listing_id = path_parts[-1] if path_parts else ""

                if not listing_id:
                    continue

                yield ListingStub(
                    listing_id=listing_id,
                    detail_url=detail_url,
                    title=title,
                )

            page_num += 1

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract title from h1.title-3
        title_elem = soup.find("h1", class_="title-3")
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract client from img.BodyTop_logo__YKhP5 alt attribute
        logo_elem = soup.find("img", class_="BodyTop_logo__YKhP5")
        client = logo_elem.get("alt") if logo_elem else None

        # Extract category: last button.breadcrumbs-text before final non-clickable span
        category = None
        breadcrumbs_container = soup.find("div", class_="Breadcrumb_scrollbarHidden__NZJMQ")
        if breadcrumbs_container:
            buttons = breadcrumbs_container.find_all("button", class_="breadcrumbs-text")
            if buttons:
                category = buttons[-1].get_text(strip=True)

        # Extract specs: 5 positional items in div.BodyTop_specs__8gRFr div.BodyTop_specsItem__FPzGn
        # [0] location, [1] duration/employment-type, [2] hours, [3] level, [4] posted_date
        # If fewer than 5, map defensively by content
        location = None
        duration = None
        hours = None
        level = None

        specs_div = soup.find("div", class_="BodyTop_specs__8gRFr")
        if specs_div:
            spec_items = specs_div.find_all("div", class_="BodyTop_specsItem__FPzGn")
            if len(spec_items) >= 5:
                location = spec_items[0].get_text(strip=True)
                duration = spec_items[1].get_text(strip=True)
                hours = spec_items[2].get_text(strip=True)
                level = spec_items[3].get_text(strip=True)
            elif len(spec_items) > 0:
                # Defensive parsing: take what's available
                location = spec_items[0].get_text(strip=True) if len(spec_items) > 0 else None
                duration = spec_items[1].get_text(strip=True) if len(spec_items) > 1 else None
                hours = spec_items[2].get_text(strip=True) if len(spec_items) > 2 else None
                level = spec_items[3].get_text(strip=True) if len(spec_items) > 3 else None

        # Extract posted_date from .BodyTop_postedSpec__hg2U0
        posted_elem = soup.find("div", class_="BodyTop_postedSpec__hg2U0")
        posted_date = posted_elem.get_text(strip=True) if posted_elem else None

        # Extract description from .BodyCenter_main__Sz_2E
        desc_elem = soup.find("div", class_="BodyCenter_main__Sz_2E")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Build JobPosting
        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
            duration=duration,
            hours=hours,
            level=level,
            posted_date=posted_date,
            rate=None,
            description=description,
        )

        return posting
