import json
from typing import Any, Iterator
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class DjinniAdapter(SiteAdapter):
    site_id: str = "djinni"
    base_url: str = "https://djinni.co"
    screenshot_selector = "div.job-post__description"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://djinni.co/jobs/keyword-QA/"

    def list_postings(self) -> Iterator[ListingStub]:
        current_url = self.LISTING_URL
        visited_pages = set()

        while current_url:
            page = fetch_page(self.fetch_strategy, current_url)
            soup = BeautifulSoup(page, "html.parser")
            cards = soup.find_all("div", class_="job-item")
            for card in cards:
                card_id = card.get("id", "")
                if not card_id.startswith("job-item-"):
                    continue

                listing_id = card_id.replace("job-item-", "")

                link = card.find("a", class_="job_item__header-link")
                if not link:
                    continue

                detail_url = link.get("href", "")
                if not detail_url:
                    continue

                title_elem = card.find("h2", class_="job-item__position")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                if detail_url.startswith("/"):
                    detail_url = self.base_url + detail_url

                yield ListingStub(
                    listing_id=listing_id,
                    detail_url=detail_url,
                    title=title,
                )

            pagination = soup.find("ul", class_="pagination")
            next_url = None
            if pagination:
                current_page = None
                active = pagination.find("li", class_="active")
                if active:
                    span = active.find("span", class_="page-link")
                    if span:
                        try:
                            current_page = int(span.get_text(strip=True))
                        except (ValueError, TypeError):
                            pass

                if current_page is not None:
                    next_page_num = current_page + 1
                    next_link = pagination.find("a", class_="page-link", string=str(next_page_num))
                    if next_link:
                        href = next_link.get("href", "")
                        if href and href.startswith("?page="):
                            next_url = urljoin(current_url, href)
                            if next_url not in visited_pages:
                                visited_pages.add(next_url)

            current_url = next_url

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        ld_json = self._extract_ld_json(soup)

        title = ld_json.get("title", "")

        client = None
        if "hiringOrganization" in ld_json:
            client = ld_json["hiringOrganization"].get("name")

        category = ld_json.get("category")

        location = None
        if "jobLocation" in ld_json:
            address = ld_json["jobLocation"].get("address", {})
            location = address.get("addressCountry")

        workplace = self._extract_workplace_options(soup) or classify_workplace(location, title)

        posted_date = ld_json.get("datePosted")

        valid_through = ld_json.get("validThrough")

        description = html_to_markdown(ld_json.get("description", ""))

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
            workplace=workplace,
            posted_date=posted_date,
            description=description,
            rate=None,
            duration=None,
            extra_fields={},
        )

        if valid_through:
            posting.extra_fields["validThrough"] = valid_through

        if "employmentType" in ld_json:
            posting.extra_fields["employmentType"] = ld_json["employmentType"]

        return posting

    def _extract_workplace_options(self, soup: BeautifulSoup) -> str | None:
        """djinni.co job pages carry a details-list entry listing every
        work arrangement the employer accepts for *this* posting (e.g.
        "Office, Remote, Hybrid Remote"), separate from the JSON-LD block.
        It's identified by content (a comma-separated match against a
        known small vocabulary), not by class, since several unrelated
        details-list entries — experience level, eligible countries —
        share the same CSS class. Unlike classify_workplace's mutual-
        exclusivity (meant for a single fixed arrangement), this field is
        a menu of accepted options: if the employer accepts fully-remote
        candidates at all, that's the practically relevant fact for a
        remote-seeking job hunter, even if Office/Hybrid are also listed.
        Returns "Fully Remote" / "Hybrid" / "On-site", or None if no such
        details-list entry is found on the page."""
        vocabulary = {"office", "remote", "hybrid remote", "hybrid", "full remote"}
        for strong in soup.find_all("strong", class_="d-block font-weight-600"):
            text = strong.get_text(strip=True)
            if not text:
                continue
            tokens = {t.strip().lower() for t in text.split(",")}
            if not tokens or not tokens.issubset(vocabulary):
                continue
            if "remote" in tokens or "full remote" in tokens:
                return "Fully Remote"
            if "hybrid" in tokens or "hybrid remote" in tokens:
                return "Hybrid"
            if "office" in tokens:
                return "On-site"
        return None

    def _extract_ld_json(self, soup: BeautifulSoup) -> dict[str, Any]:
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            if not script.string:
                continue

            try:
                data = json.loads(script.string)

                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        return data
                    elif "@graph" in data:
                        for item in data.get("@graph", []):
                            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                                return item
            except json.JSONDecodeError:
                continue

        return {}
