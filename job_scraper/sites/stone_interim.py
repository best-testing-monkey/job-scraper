import json
import re
import urllib.parse
from typing import Any, ClassVar, Iterator

from scrapling.fetchers import Fetcher

from job_scraper.core.html_markdown import html_to_markdown
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy


class StoneInterimAdapter(SiteAdapter):
    site_id = "stone_interim"
    base_url = "https://www.stone-interim.nl"
    screenshot_selector = None  # BLOCKED: saved human page has no description (client-rendered)
    fetch_strategy = FetchStrategy.STATIC
    raw_format: ClassVar[str] = "json"
    LISTING_API_URL = "https://www.stone-interim.nl/api/v1/WordPress/GetOverviewItems/"

    def __init__(self) -> None:
        self._link_cache: dict[str, str] = {}

    def list_postings(self) -> Iterator[ListingStub]:
        response = Fetcher.post(
            self.LISTING_API_URL,
            json={
                "pageKind": "job-overview",
                "file_name": "job-overview",
                "lang": "",
                "taxonomies_to_filter": [],
                "searchQuery": "",
                "start_index": 0,
                "page_size": 50,
            },
        )
        data = json.loads(response.body)

        for item in data.get("Items", []):
            title = item.get("Title", "")
            link_url = item.get("LinkUrl", "")

            if not title or not link_url:
                continue

            match = re.search(r"/id/(\d+)/", link_url)
            if not match:
                continue

            listing_id = match.group(1)
            self._link_cache[listing_id] = urllib.parse.urljoin(self.base_url + "/", link_url)
            detail_url = f"https://www.stone-interim.nl/api/v1/WordPress/GetVacancy/{listing_id}"

            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        source_url = self._link_cache.get(stub.listing_id)
        if source_url is None:
            raise ValueError(
                f"No human LinkUrl cached for stone_interim listing {stub.listing_id}; "
                "list_postings must run first"
            )
        data = json.loads(page)
        cr = data.get("ToVacancy", {}).get("CRVacancy", {})

        title = data.get("TitleInformation", "")
        posted_date = data.get("PublicationStart")
        publication_end = data.get("PublicationEnd")

        client = cr.get("CompanyName")
        hours = str(cr.get("HoursPerWeek", "")) if cr.get("HoursPerWeek") else None

        location = None
        province_node = cr.get("ToProvince1Node", {}).get("CRDataNode", {})
        if province_node:
            location = province_node.get("Value")

        workplace = classify_workplace(location)

        category = None
        function_level = cr.get("ToFunctionLevel1", {}).get("CRDataNode", {})
        if function_level:
            category = function_level.get("Value")

        duration_parts = []
        contract_type = cr.get("ToContractTypeNode", {}).get("CRDataNode", {})
        if contract_type:
            contract_value = contract_type.get("Value")
            if contract_value:
                duration_parts.append(contract_value)

        product_type = cr.get("ToProductNode", {}).get("CRDataNode", {})
        if product_type:
            product_value = product_type.get("Value")
            if product_value:
                duration_parts.append(product_value)

        duration = " ".join(duration_parts) if duration_parts else None

        description = self._extract_description(cr)

        posting = JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=source_url,
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
            extra_fields={},
        )

        if publication_end:
            posting.extra_fields["PublicationEnd"] = publication_end

        return posting

    def _extract_description(self, cr: dict[str, Any]) -> str:
        description_parts = []

        for field in ["IntroInformation", "VacancyInformation", "OfferInformation", "Requirements", "CompanyInformation"]:
            text = cr.get(field, "")
            if text:
                converted = html_to_markdown(text)
                if converted:
                    description_parts.append(converted)

        return "\n\n".join(description_parts)
