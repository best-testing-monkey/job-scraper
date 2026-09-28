from typing import Any, Iterator

from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class IctergezochtAdapter(SiteAdapter):
    site_id: str = "ictergezocht"
    base_url: str = "https://www.ictergezocht.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    LISTING_URL: str = "https://www.ictergezocht.nl/ict-vacatures/"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(
            self.fetch_strategy,
            self.LISTING_URL,
            solve_cloudflare=True,
            network_idle=True,
        )
        soup = BeautifulSoup(page, "html.parser")
        cards = soup.find_all("section", class_="feed-card")
        for card in cards:
            listing_id = card.get("data-vacancyid", "")
            if not listing_id:
                continue
            title_elem = card.find("h3")
            if not title_elem:
                continue
            title_link = title_elem.find("a", class_="feed-card__link")
            if not title_link:
                continue
            title = title_link.get_text(strip=True)
            detail_url_path = card.get("data-url", "")
            if not detail_url_path:
                continue
            detail_url = f"{self.base_url}{detail_url_path}"
            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(page, "html.parser")

        title_elem = soup.find("div", class_="vacancy-title-heading")
        title = title_elem.get_text(strip=True) if title_elem else stub.title

        client = self._extract_client(soup)
        location = self._extract_location(soup)
        category = self._extract_category(soup)
        hours = self._extract_hours(soup)
        rate = self._extract_rate(soup)
        contract_type = self._extract_contract_type(soup)
        description = self._extract_description(soup)

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            location=location,
            category=category,
            hours=hours,
            rate=rate,
            description=description,
            posted_date=None,
            duration=None,
            scrape_note="Pagination is non-functional (all pages return page-1 content); page 1 only",
        )
        if contract_type:
            posting.extra_fields["contract_type"] = contract_type
        return posting

    def _extract_client(self, soup: BeautifulSoup) -> str | None:
        company_meta = soup.find("div", class_="vacancy-company-meta")
        if not company_meta:
            return None
        logo_title = company_meta.find("div", class_="logo-title")
        if not logo_title:
            return None
        span = logo_title.find("span")
        if not span:
            return None
        return span.get_text(strip=True)

    def _extract_location(self, soup: BeautifulSoup) -> str | None:
        component_location = soup.find("section", class_="component-location")
        if not component_location:
            return None
        spans = component_location.find_all("span")
        if not spans:
            return None
        for span in spans:
            text = span.get_text(strip=True)
            if text and not span.get("class") or "wfh-element" not in (
                span.get("class", []) if isinstance(span.get("class"), list) else []
            ):
                if text not in ["Locatie", "Deels thuiswerken"]:
                    return text
        return None

    def _extract_category(self, soup: BeautifulSoup) -> str | None:
        hero_oneliners = soup.find("section", class_="hero-oneliners")
        if not hero_oneliners:
            return None
        component_list = hero_oneliners.find("div", class_="component-list-list")
        if not component_list:
            return None
        divs = component_list.find_all("div", recursive=False)
        if not divs:
            return None
        categories = [div.get_text(strip=True) for div in divs]
        return " ".join(categories) if categories else None

    def _extract_hours(self, soup: BeautifulSoup) -> str | None:
        specs = soup.find_all("section", class_="component-spec")
        for spec in specs:
            icon = spec.find("i", class_="vo-icon")
            if not icon:
                continue
            aria_label = icon.get("aria-label", "")
            if "uur" in aria_label.lower():
                spec_value = spec.find("span", class_="spec-value")
                if spec_value:
                    return spec_value.get_text(strip=True)
        return None

    def _extract_rate(self, soup: BeautifulSoup) -> str | None:
        specs = soup.find_all("section", class_="component-spec")
        for spec in specs:
            icon = spec.find("i", class_="vo-icon")
            if not icon:
                continue
            icon_classes = icon.get("class", [])
            if isinstance(icon_classes, list):
                icon_class_str = " ".join(icon_classes)
            else:
                icon_class_str = str(icon_classes)
            if "currency-euro-circle" in icon_class_str:
                spec_value = spec.find("span", class_="spec-value")
                if spec_value:
                    return spec_value.get_text(strip=True)
        return None

    def _extract_contract_type(self, soup: BeautifulSoup) -> str | None:
        specs = soup.find_all("section", class_="component-spec")
        for spec in specs:
            icon = spec.find("i", class_="vo-icon")
            if not icon:
                continue
            icon_classes = icon.get("class", [])
            if isinstance(icon_classes, list):
                icon_class_str = " ".join(icon_classes)
            else:
                icon_class_str = str(icon_classes)
            if "briefcase-02" in icon_class_str:
                spec_value = spec.find("span", class_="spec-value")
                if spec_value:
                    return spec_value.get_text(strip=True)
        return None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        description_elem = soup.find("div", class_="vacancy-full-text-dom")
        if description_elem:
            return description_elem.get_text(strip=True)
        return ""
