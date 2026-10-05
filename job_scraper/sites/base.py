from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Iterator

from scrapling.fetchers import Fetcher, StealthyFetcher

from job_scraper.core.gone import GoneCheck, gone_reason
from job_scraper.core.models import JobPosting, ListingStub


class FetchStrategy(Enum):
    STATIC = "static"
    STEALTH = "stealth"
    DYNAMIC = "dynamic"


class PostingGone(Exception):
    """Raised when a detail page indicates the posting is no longer available."""
    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"{url}: {reason}")


def fetch_page(strategy: "FetchStrategy", url: str, *, gone_check: GoneCheck | None = None, **kwargs: Any) -> bytes:
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
    NotImplementedError.

    If gone_check is not None, checks the response for indicators that the
    posting is gone (404/410 status, redirect to listing page, or gone markers
    in title/h1). Raises PostingGone if any indicator is found. With gone_check=None,
    the function behaves exactly as before."""
    if strategy == FetchStrategy.STATIC:
        resp = Fetcher.get(url, **kwargs)
    elif strategy == FetchStrategy.STEALTH:
        resp = StealthyFetcher.fetch(url, headless=True, **kwargs)
    else:
        raise NotImplementedError(f"Fetch strategy {strategy.value} not yet implemented")

    if gone_check is not None:
        status = getattr(resp, "status", None)
        final_url = getattr(resp, "url", None)
        reason = gone_reason(status, url, final_url, resp.body, gone_check)
        if reason is not None:
            raise PostingGone(url, reason)

    return resp.body


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
    screenshot_skip_selectors: ClassVar[tuple[str, ...]] = ()
    """CSS selectors (valid for Playwright); if any of these matches after load, the
    page is a gate/teaser: skip the screenshot."""
    screenshot_min_height: ClassVar[int] = 100
    """Minimum element height in pixels; captures shorter than this are skipped on purpose."""
    listing_paths: ClassVar[tuple[str, ...]] = ()
    """URL paths of the site's listing/landing pages; a detail fetch that redirects
    to one means the posting is gone."""
    gone_markers: ClassVar[tuple[str, ...]] = ()
    """Case-insensitive texts of a soft-404 page, matched against <title>/<h1> only."""

    @classmethod
    def gone_check(cls, listing_id: str = "") -> GoneCheck:
        """Return a GoneCheck configured for this adapter."""
        return GoneCheck(listing_id, cls.listing_paths, cls.gone_markers)

    @abstractmethod
    def list_postings(self) -> Iterator[ListingStub]: ...

    @abstractmethod
    def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting: ...
