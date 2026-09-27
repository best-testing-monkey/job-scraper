from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Iterator

from scrapling.fetchers import Fetcher

from job_scraper.core.models import JobPosting, ListingStub


class FetchStrategy(Enum):
    STATIC = "static"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"


def fetch_page(strategy: "FetchStrategy", url: str) -> str:
    """Dispatches to the right Scrapling fetcher for this strategy and
    returns the fetched page's HTML as a plain string.
    FetchStrategy.STATIC -> scrapling.fetchers.Fetcher.get(url).html_content.
    The other two strategies (STEALTH, DYNAMIC) are out of scope this
    phase: raises NotImplementedError naming the strategy."""
    if strategy == FetchStrategy.STATIC:
        return Fetcher.get(url).html_content
    raise NotImplementedError(f"Fetch strategy {strategy.value} not yet implemented")


class SiteAdapter(ABC):
    site_id: ClassVar[str]
    base_url: ClassVar[str]
    fetch_strategy: ClassVar[FetchStrategy] = FetchStrategy.STATIC

    @abstractmethod
    def list_postings(self) -> Iterator[ListingStub]: ...

    @abstractmethod
    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting: ...
