import json
import re
from typing import Any, Iterator
from bs4 import BeautifulSoup

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.core.workplace import classify_workplace
from job_scraper.sites.base import SiteAdapter, FetchStrategy, fetch_page


class TenderLinkAdapter(SiteAdapter):
    site_id: str = "tender_link"
    base_url: str = "https://tender-link.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://tender-link.nl/wp-json/sdcx/v2/vacancies/all"

    def __init__(self) -> None:
        self._vacancy_cache: dict[str, dict[str, Any]] = {}

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        data = json.loads(page)
        vacancies = data.get("vacancies", [])
        for vacancy in vacancies:
            publication_id = str(vacancy.get("publicationID", ""))
            slug = vacancy.get("slug", "")
            title = vacancy.get("jobTitle", "")
            if not publication_id or not slug:
                continue
            detail_url = f"https://tender-link.nl/vacature/{slug}/"
            self._vacancy_cache[publication_id] = vacancy
            yield ListingStub(
                listing_id=publication_id,
                detail_url=detail_url,
                title=title,
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        vacancy = self._vacancy_cache.get(stub.listing_id, {})
        title = vacancy.get("jobTitle", "") or vacancy.get("titleInformation", "")
        client = vacancy.get("companyName", "")
        category = vacancy.get("toCategoryNode", "")
        location = vacancy.get("workLocation", "") or vacancy.get("toProvince1Node", "")
        hours = str(vacancy.get("hoursPerWeek", "")) if vacancy.get("hoursPerWeek") else ""
        duration = vacancy.get("contractPeriod", "")
        posted_date = vacancy.get("publicationStart", "")
        description = self._extract_description(vacancy)
        extra_fields: dict[str, str] = {}
        branche = vacancy.get("toBrancheLevel2", "")
        if branche:
            extra_fields["Branche"] = branche
        vacancy_no = vacancy.get("vacancyNo", "")
        if vacancy_no:
            extra_fields["vacancyNo"] = vacancy_no
        rate = self._extract_rate(vacancy)
        salaried_gross = self._extract_salaried_gross(vacancy)
        if salaried_gross:
            extra_fields["salaried_gross_monthly"] = salaried_gross

        # Extract and translate workplace signal
        workplace_signal = vacancy.get("toWorkplaceTypeNode", "")
        if workplace_signal:
            workplace_signal = self._translate_workplace_signal(workplace_signal)
        else:
            workplace_signal = None

        workplace = classify_workplace(location, workplace_signal)

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
            duration=duration,
            posted_date=posted_date,
            description=description,
            extra_fields=extra_fields,
        )
        return posting

    def _extract_description(self, vacancy: dict[str, Any]) -> str:
        parts = []
        for field in [
            "introInformation",
            "companyInformation",
            "vacancyInformation",
            "offerInformation",
            "requirementsInformation",
            "functionContactInformation",
        ]:
            text = vacancy.get(field, "")
            if text:
                soup = BeautifulSoup(text, "html.parser")
                stripped = soup.get_text(separator=" ", strip=True)
                if stripped:
                    parts.append(stripped)
        return " ".join(parts)

    def _extract_rate(self, vacancy: dict[str, Any]) -> str | None:
        min_salary = vacancy.get("minSalary")
        max_salary = vacancy.get("maxSalary")
        period = vacancy.get("toSalaryPeriodNode", "")
        if min_salary is not None and max_salary is not None:
            return f"{min_salary}-{max_salary} {period}".strip()
        return None

    def _extract_salaried_gross(self, vacancy: dict[str, Any]) -> str | None:
        additional_info = vacancy.get("additionalInfo", {})
        vacancy_info = additional_info.get("vacancy", {})
        salaried_key = "10722"
        if salaried_key in vacancy_info:
            return vacancy_info[salaried_key].get("value")
        return None

    def _translate_workplace_signal(self, workplace_nl: str) -> str | None:
        """Translate Dutch workplace keywords to English equivalents for classify_workplace.
        Returns the translated signal, or the original text if no translation matches."""
        if not workplace_nl:
            return None
        workplace_lower = workplace_nl.lower()
        if "hybride" in workplace_lower or "hybrid" in workplace_lower:
            return "Hybrid"
        elif (
            "remote" in workplace_lower
            or "thuiswerken" in workplace_lower
            or "volledig remote" in workplace_lower
            or "deels thuiswerken" in workplace_lower
        ):
            return "Fully Remote"
        elif "op locatie" in workplace_lower or "ter plaatse" in workplace_lower or "on-site" in workplace_lower:
            return "On-site"
        else:
            # Pass as-is to classify_workplace
            return workplace_nl
