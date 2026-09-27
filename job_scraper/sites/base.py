from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Iterator

from job_scraper.core.models import JobPosting, ListingStub


class FetchStrategy(Enum):
    STATIC = "static"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"


class SiteAdapter(ABC):
    site_id: ClassVar[str]
    base_url: ClassVar[str]
    fetch_strategy: ClassVar[FetchStrategy] = FetchStrategy.STATIC

    @abstractmethod
    def list_postings(self) -> Iterator[ListingStub]: ...

    @abstractmethod
    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting: ...
