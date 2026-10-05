import re
from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class WearedevelopersAdapter(SiteAdapter):
    site_id: str = "wearedevelopers"
    base_url: str = "https://www.wearedevelopers.com"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    # The "Job description" block is always the 3rd <section> of the detail
    # column (after "Role details" and "Tech stack"); plain CSS, no :has().
    screenshot_selector = "div.flex-col.gap-8.pb-8 > section:nth-of-type(3)"
    screenshot_hide_selectors = (
        "header.sticky",
        "dialog#modal",
        "div.fixed.inset-0",
        ".tru_overlay",
        ".tru_cookie-dialog_wrapper",
    )
    # Live: the TrustArc overlay stays displayed despite the hide rule, so also
    # click its "Necessary only" button (normal consent decline).
    screenshot_pre_actions = ("#tru_deselect_btn",)
    LISTING_URL: str = "https://www.wearedevelopers.com/jobs?country=all&q=QA"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(page, "html.parser")
        articles = soup.find_all("article")

        for article in articles:
            link = article.find("a", href=re.compile(r"^/jobs/ext/"))
            if not link:
                continue

            href = link.get("href", "")
            match = re.match(r"^/jobs/ext/(\d+)-", href)
            if not match:
                continue

            listing_id = match.group(1)
            title_elem = article.find("h3")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            detail_url = f"{self.base_url}{href}"

            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        h1_elem = soup.find("h1")
        title = h1_elem.get_text(strip=True) if h1_elem else stub.title

        location = self._get_meta_content(soup, "job:location")
        workplace_badge = self._get_workplace_badge(soup)
        workplace = classify_workplace(location, workplace_badge)
        posted_date = self._get_meta_content(soup, "job:posted_time")
        client = self._get_meta_content(soup, "og:article:author", is_property=True)

        skills = self._get_all_meta_content(soup, "job:skill")
        category = " ".join(skills) if skills else None

        description = self._extract_description(soup)

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            location=location,
            workplace=workplace,
            posted_date=posted_date,
            category=category,
            description=description,
            rate=None,
            hours=None,
            duration=None,
            scrape_note="Page 1 only — pagination is a Hotwire/Turbo 'Load more' mechanism not yet supported",
        )

        extra_fields = self._get_meta_content(soup, "job:employment_type")
        if extra_fields:
            posting.extra_fields["employment_type"] = extra_fields

        return posting

    def _get_meta_content(
        self, soup: BeautifulSoup, name: str, is_property: bool = False
    ) -> str | None:
        attr_name = "property" if is_property else "name"
        meta = soup.find("meta", {attr_name: name})
        if meta:
            return meta.get("content")
        return None

    def _get_all_meta_content(self, soup: BeautifulSoup, name: str) -> list[str]:
        metas = soup.find_all("meta", {"name": name})
        return [meta.get("content") for meta in metas if meta.get("content")]

    def _get_workplace_badge(self, soup: BeautifulSoup) -> str | None:
        """Text of the site's workplace-type pill badge (e.g. "Remote"),
        identified by its distinctive amber styling rather than by exact
        class-list match, so minor Tailwind class reordering/additions
        don't silently break extraction. Returns None if no such badge is
        present (most postings show no badge at all, implying on-site/
        unspecified — see classify_workplace, which treats "no signal" as
        unknown rather than assuming on-site)."""
        badge = soup.find(
            "span", class_=lambda c: c and "bg-amber-500/10" in c and "text-amber-700" in c
        )
        return badge.get_text(strip=True) if badge else None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        h2_elems = soup.find_all("h2")
        for h2 in h2_elems:
            if h2.get_text(strip=True) == "Job description":
                next_div = h2.find_next("div", class_="prose-base-content")
                if next_div:
                    return html_to_markdown(str(next_div))
        return ""
