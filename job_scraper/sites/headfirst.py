import json
import re
from typing import Any, Iterator

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import FetchStrategy, SiteAdapter, fetch_page

_CHUNK_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.DOTALL)
_JOB_ENTITY_MARKER = '"entity":"job_request"'
_NO_DESCRIPTION_NOTE = (
    "Full description not extracted — see headfirst.nl or the broker_url "
    "for details."
)


def _unescape_chunk(raw: str) -> str:
    return json.loads('"' + raw + '"')


def _find_job_chunk(html_text: str) -> str | None:
    for raw in _CHUNK_PATTERN.findall(html_text):
        unescaped = _unescape_chunk(raw)
        if _JOB_ENTITY_MARKER in unescaped:
            return unescaped
    return None


def _extract_job_objects(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_spans: set[tuple[int, int]] = set()
    for match in re.finditer(re.escape(_JOB_ENTITY_MARKER), text):
        start = text.rfind('{"id":"', 0, match.start())
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    span = (start, i + 1)
                    if span not in seen_spans:
                        seen_spans.add(span)
                        try:
                            results.append(json.loads(text[start : i + 1]))
                        except json.JSONDecodeError:
                            pass
                    break
    return results


def _job_objects_from_page(page: Any) -> list[dict[str, Any]]:
    html_text = page.decode("utf-8") if isinstance(page, (bytes, bytearray)) else page
    chunk = _find_job_chunk(html_text)
    if chunk is None:
        return []
    return _extract_job_objects(chunk)


def _format_hours(job: dict[str, Any]) -> str | None:
    min_hours = job.get("hoursPerWeekMin")
    max_hours = job.get("hoursPerWeekMax")
    if min_hours is None or max_hours is None:
        return None
    return f"{min_hours}-{max_hours}"


def _format_duration(job: dict[str, Any]) -> str | None:
    start_date = job.get("startDate")
    end_date = job.get("endDate")
    if not start_date or not end_date:
        return None
    return f"{start_date.split('T')[0]} - {end_date.split('T')[0]}"


class HeadfirstAdapter(SiteAdapter):
    site_id: str = "headfirst"
    base_url: str = "https://www.headfirst.nl"
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC
    LISTING_URL: str = "https://www.headfirst.nl/vind-opdrachten/"

    def list_postings(self) -> Iterator[ListingStub]:
        page = fetch_page(self.fetch_strategy, self.LISTING_URL)
        for job in _job_objects_from_page(page):
            yield ListingStub(
                listing_id=job["id"],
                detail_url=self.LISTING_URL,
                title=job.get("title", ""),
            )

    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
        job = next(
            (j for j in _job_objects_from_page(page) if j.get("id") == stub.listing_id),
            {},
        )
        extra_fields: dict[str, str] = {}
        if job.get("referenceCode"):
            extra_fields["referenceCode"] = job["referenceCode"]
        if job.get("brokerUrl"):
            extra_fields["apply_url"] = job["brokerUrl"]
        return JobPosting(
            site_id=self.site_id,
            listing_id=stub.listing_id,
            source_url=self.LISTING_URL,
            title=job.get("title", stub.title),
            client=job.get("clientName"),
            category=None,
            location=job.get("location"),
            hours=_format_hours(job),
            rate=None,
            duration=_format_duration(job),
            posted_date=job.get("publishedDate"),
            description="",
            scrape_note=_NO_DESCRIPTION_NOTE,
            extra_fields=extra_fields,
        )
