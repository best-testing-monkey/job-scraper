from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Iterator

from scrapling.fetchers import Fetcher, StealthyFetcher

from job_scraper.core.models import JobPosting, ListingStub


class FetchStrategy(Enum):
    STATIC = "static"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"


def fetch_page(strategy: "FetchStrategy", url: str, **kwargs: Any) -> bytes:
    """Dispatches to the right Scrapling fetcher for this strategy and
    returns the fetched page's raw response body as bytes (not
    .html_content, which is empty for non-HTML responses like JSON/XML —
    .body works uniformly for HTML, JSON, and XML, and every parser used
    in this project — BeautifulSoup, json.loads, ElementTree — accepts
    bytes directly).
    FetchStrategy.STATIC -> scrapling.fetchers.Fetcher.get(url, **kwargs).body.
    FetchStrategy.STEALTH -> scrapling.fetchers.StealthyFetcher.fetch(url,
    headless=True, **kwargs).body — a real anti-detect browser (Camoufox),
    for sites behind bot-mitigation WAFs that block plain HTTP entirely.
    Extra kwargs pass straight through to the underlying fetcher call —
    e.g. solve_cloudflare=True, network_idle=True for a site whose
    StealthyFetcher call needs Cloudflare-challenge solving.
    FetchStrategy.DYNAMIC is out of scope this phase: raises
    NotImplementedError."""
    if strategy == FetchStrategy.STATIC:
        return Fetcher.get(url, **kwargs).body
    if strategy == FetchStrategy.STEALTH:
        return StealthyFetcher.fetch(url, headless=True, **kwargs).body
    raise NotImplementedError(f"Fetch strategy {strategy.value} not yet implemented")


class SiteAdapter(ABC):
    site_id: ClassVar[str]
    base_url: ClassVar[str]
    fetch_strategy: ClassVar[FetchStrategy] = FetchStrategy.STATIC
    raw_format: ClassVar[str] = "html"
    """File extension for the raw saved detail page (see raw_export.write).
    Override to "json" for adapters whose detail fetch returns a JSON API
    response rather than an HTML page."""
    screenshot_selector: ClassVar[str | None] = None
    """CSS selector (valid for both Playwright and soupsieve/bs4 — no :contains())
    matching exactly ONE element that wraps only the job description; None means
    no screenshots for this site."""
    screenshot_hide_selectors: ClassVar[tuple[str, ...]] = ()
    """CSS selectors (valid for both Playwright and soupsieve/bs4) of elements to
    hide (cookie banners, consent dialogs, apply forms, share bars) before the
    element screenshot is taken; empty means hide only the generic overlays."""
    screenshot_pre_actions: ClassVar[tuple[str, ...]] = ()
    """CSS selectors (valid for Playwright) of elements to click, each once and in
    order, after the page loads and before the element screenshot (e.g. a "Show
    more" button); a missing or unclickable selector is skipped."""

    @abstractmethod
    def list_postings(self) -> Iterator[ListingStub]: ...

    @abstractmethod
    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting: ...
