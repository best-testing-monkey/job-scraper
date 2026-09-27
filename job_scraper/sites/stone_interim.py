import json
import re
from typing import Any, Iterator

from scrapling.fetchers import Fetcher

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import SiteAdapter, FetchStrategy


class StoneInterimAdapter(SiteAdapter):
    site_id = "stone_interim"
    base_url = "https://www.stone-interim.nl"
    fetch_strategy = FetchStrategy.STATIC
    LISTING_API_URL = "https://www.stone-interim.nl/api/v1/WordPress/GetOverviewItems/"

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
            detail_url = f"https://www.stone-interim.nl/api/v1/WordPress/GetVacancy/{listing_id}"

            yield ListingStub(
                listing_id=listing_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
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
            source_url=stub.detail_url,
            title=title,
            client=client,
            category=category,
            location=location,
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
                description_parts.append(text)

        full_text = " ".join(description_parts)
        full_text = self._strip_html(full_text)
        full_text = re.sub(r"\s+", " ", full_text)
        return full_text.strip()

    def _strip_html(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&apos;", "'", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&ldquo;", '"', text)
        text = re.sub(r"&rdquo;", '"', text)
        text = re.sub(r"&rsquo;", "'", text)
        text = re.sub(r"&eacute;", "é", text)
        text = re.sub(r"&#\d+;", "", text)
        return text
