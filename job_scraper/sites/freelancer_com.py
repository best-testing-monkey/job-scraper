import re
from typing import Any, Iterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class FreelancerComAdapter(SiteAdapter):
    site_id: str = "freelancer_com"
    base_url: str = "https://www.freelancer.com"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://www.freelancer.com/jobs/software-testing/"

    def list_postings(self) -> Iterator[ListingStub]:
        current_url = self.LISTING_URL
        while current_url:
            page = fetch_page(self.fetch_strategy, current_url)
            soup = BeautifulSoup(page, "html.parser")

            # Find all job cards
            cards = soup.find_all(
                "div",
                class_="JobSearchCard-item-inner",
                attrs={"data-project-card": "true"},
            )

            for card in cards:
                link = card.find("a", class_="JobSearchCard-primary-heading-link")
                if not link:
                    continue

                title = link.get_text(strip=True)
                detail_url = link.get("href", "")
                if not detail_url:
                    continue

                # Ensure absolute URL
                if detail_url.startswith("/"):
                    detail_url = self.base_url + detail_url

                # Extract listing_id from the URL path (final segment)
                match = re.search(r"/([a-z0-9-]+)$", detail_url)
                if not match:
                    continue
                listing_id = match.group(1)

                yield ListingStub(
                    listing_id=listing_id,
                    detail_url=detail_url,
                    title=title,
                )

            # Look for next page link in pagination
            pagination = soup.find("div", class_="Pagination")
            next_url = None
            if pagination:
                next_link = pagination.find("a", class_="Pagination-item", attrs={"rel": "next"})
                if next_link:
                    next_href = next_link.get("href")
                    if next_href:
                        next_url = urljoin(self.LISTING_URL, next_href)
                        # Avoid infinite loops: stop if next_url is same as current
                        if next_url == current_url:
                            next_url = None

            current_url = next_url

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        # Extract title from h1
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        # Extract rate from h2 immediately after h1
        rate = None
        if h1:
            h2 = h1.find_next("h2")
            if h2:
                rate = h2.get_text(strip=True)

        # Extract posted_date: "Posted" text + fl-relative-time span
        posted_date = None
        page_text = soup.get_text()
        # Look for Posted pattern with relative time
        posted_match = re.search(
            r"Posted\s+(\d+\s*(?:minute|hour|day|week|month|year)s?\s*ago)",
            page_text,
            re.IGNORECASE,
        )
        if posted_match:
            posted_date = posted_match.group(1)

        # Extract duration: plain <p> after "•" separator
        duration = None
        # Look for duration pattern (e.g., "Ends in 20 hours")
        duration_match = re.search(
            r"Ends in\s+(\d+\s*(?:hour|day|week|month)s?)",
            page_text,
            re.IGNORECASE,
        )
        if duration_match:
            duration = duration_match.group(0)

        # Extract description from p.Project-description.whitespace-pre-line
        description = ""
        desc_elem = soup.find("p", class_="Project-description")
        if desc_elem:
            # Check if element has nested HTML tags
            has_nested_tags = any(hasattr(child, 'name') and child.name for child in desc_elem.children)
            if has_nested_tags:
                # Element has HTML structure - use decode_contents
                description = html_to_markdown(desc_elem.decode_contents())
            else:
                # Plain text - use a placeholder for & so it goes through plain text path
                text = desc_elem.get_text()
                amp_placeholder = "\x00AMP\x00"
                text_processed = text.replace("&", amp_placeholder)
                result = html_to_markdown(text_processed)
                description = result.replace(amp_placeholder, "&")

        # Extract category from fl-tag[fltrackinglabel="ProjectViewLoggedOut-SkillTag"]
        category = None
        skill_tags = soup.find_all(
            "fl-tag", attrs={"fltrackinglabel": "ProjectViewLoggedOut-SkillTag"}
        )
        if skill_tags:
            # Join all skill tags with "/"
            category = "/".join([tag.get_text(strip=True) for tag in skill_tags])

        # Extract workplace from the IconText project details section
        workplace_text = self._extract_workplace_text(soup)
        workplace = classify_workplace(workplace_text)

        # Client is always None on Freelancer.com logged-out view
        client = None

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            rate=rate,
            duration=duration,
            posted_date=posted_date,
            description=description,
            workplace=workplace,
            extra_fields={},
        )

        return posting

    def _extract_workplace_text(self, soup: BeautifulSoup) -> str | None:
        """Extract workplace text from the project details IconText columns.
        Looks for text like 'Remote project', 'Hybrid project', etc."""
        fl_cols = soup.find_all("fl-col", class_="IconText")
        for col in fl_cols:
            p = col.find("p")
            if p:
                text = p.get_text(strip=True)
                # Check if this text contains workplace-related keywords
                if any(
                    keyword in text.lower()
                    for keyword in ["remote", "hybrid", "on-site", "onsite"]
                ):
                    return text
        return None
