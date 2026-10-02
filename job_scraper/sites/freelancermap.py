import json
import re
from typing import Any, Iterator

from bs4 import BeautifulSoup, Tag

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import FetchStrategy, SiteAdapter, fetch_page

_PAGINATION_NOTE = (
    "Page 1 only — the ?pagenr=N query param does not paginate on "
    "freelancermap (confirmed dead param, real pagination is click/XHR-only); "
    "~22 results total for this search."
)

_POSTED_DATE_RE = re.compile(r"veröffentlicht am\s+(\d{2}\.\d{2}\.\d{4})")


def _decode(page: Any) -> str:
    return page.decode("utf-8") if isinstance(page, (bytes, bytearray)) else page


def _find_component_json(
    soup: BeautifulSoup, component_name: str
) -> dict[str, Any] | None:
    script = soup.find(
        "script",
        attrs={
            "class": "js-react-on-rails-component",
            "data-component-name": component_name,
        },
    )
    if script is None or not script.string:
        return None
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        return None


def _badge_text(badge: Tag) -> str:
    text = ""
    for part in badge.stripped_strings:
        if text and part[0] not in ",.%":
            text += " "
        text += part
    return text


def _badge_for_icon(soup: BeautifulSoup, *icon_classes: str) -> str | None:
    icon = soup.select_one("i." + ".".join(icon_classes))
    if icon is None:
        return None
    badge = icon.find_parent(class_="badge")
    if badge is None:
        return None
    return _badge_text(badge)


class FreelancermapAdapter(SiteAdapter):
    site_id: str = "freelancermap"
    base_url: str = "https://www.freelancermap.de"
    fetch_strategy: FetchStrategy = FetchStrategy.STEALTH
    LISTING_URL: str = "https://www.freelancermap.de/projekte?query=Playwright"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        soup = BeautifulSoup(_decode(page), "html.parser")
        data = _find_component_json(soup, "ProjectSearch")
        results = data.get("initialResults", []) if data else []
        for project in results:
            slug = project.get("slug")
            project_id = project.get("id")
            if not slug or project_id is None:
                continue
            yield ListingStub(
                listing_id=str(project_id),
                detail_url=f"{self.base_url}/projekt/{slug}",
                title=project.get("title", ""),
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        soup = BeautifulSoup(_decode(page), "html.parser")

        title_elem = soup.select_one("h1.h2.mg-b-display-m")
        title = title_elem.get_text(strip=True) if title_elem else stub.title

        show_data = _find_component_json(soup, "ProjectShow")
        project_data = (show_data or {}).get("project", {})
        client = project_data.get("company") or None

        location = _badge_for_icon(soup, "far", "fa-location-pin")
        contract_type = _badge_for_icon(soup, "far", "fa-file-contract")
        start_date = _badge_for_icon(soup, "far", "fa-calendar")
        duration = _badge_for_icon(soup, "far", "fa-hourglass")
        hours = _badge_for_icon(soup, "far", "fa-briefcase")

        # Extract workplace classification from remoteInPercent
        workplace_signal = None
        contract_info = project_data.get("contractType", {})
        if isinstance(contract_info, dict):
            remote_percent = contract_info.get("remoteInPercent")
            if remote_percent == 100:
                workplace_signal = "100% remote"
            elif isinstance(remote_percent, int) and 0 < remote_percent < 100:
                workplace_signal = "Hybrid"
        workplace = classify_workplace(location, workplace_signal)

        posted_date = None
        posted_match = _POSTED_DATE_RE.search(soup.get_text())
        if posted_match:
            posted_date = posted_match.group(1)

        keyword_links = soup.find_all(
            "a", attrs={"data-id": "project-body-keyword-link"}
        )
        category = (
            ", ".join(link.get_text(strip=True) for link in keyword_links) or None
        )

        description_elem = soup.select_one("div.project-body-description .ql-editor")
        description = (
            description_elem.get_text(" ", strip=True) if description_elem else ""
        )

        extra_fields: dict[str, str] = {}
        if contract_type:
            extra_fields["contract_type"] = contract_type
        if start_date:
            extra_fields["start_date"] = start_date

        return JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
            workplace=workplace,
            hours=hours,
            rate=None,
            duration=duration,
            posted_date=posted_date,
            description=description,
            scrape_note=_PAGINATION_NOTE,
            extra_fields=extra_fields,
        )
