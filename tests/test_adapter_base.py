from typing import Any, Iterator
from unittest.mock import patch

import pytest

from job_scraper.core.gone import GoneCheck
from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import FetchStrategy, PostingGone, SiteAdapter, fetch_page


def test_fetch_strategy_members() -> None:
    assert FetchStrategy.STATIC.value == "static"
    assert FetchStrategy.STEALTH.value == "stealth"
    assert FetchStrategy.DYNAMIC.value == "dynamic"


def test_site_adapter_cannot_instantiate_without_list_postings() -> None:
    class IncompleteAdapter(SiteAdapter):
        site_id = "incomplete"
        base_url = "http://example.com"

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

    with pytest.raises(TypeError):
        IncompleteAdapter()


def test_site_adapter_cannot_instantiate_without_parse_detail() -> None:
    class IncompleteAdapter(SiteAdapter):
        site_id = "incomplete"
        base_url = "http://example.com"

        def list_postings(self) -> Iterator[ListingStub]:
            return iter([])

    with pytest.raises(TypeError):
        IncompleteAdapter()


def test_site_adapter_concrete_subclass_instantiation() -> None:
    class ConcreteAdapter(SiteAdapter):
        site_id = "test_site"
        base_url = "http://test.example.com"

        def list_postings(self) -> Iterator[ListingStub]:
            return iter([])

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

    adapter = ConcreteAdapter()
    assert adapter.site_id == "test_site"
    assert adapter.base_url == "http://test.example.com"
    assert adapter.fetch_strategy == FetchStrategy.STATIC


def test_site_adapter_custom_fetch_strategy() -> None:
    class CustomStrategyAdapter(SiteAdapter):
        site_id = "custom_site"
        base_url = "http://custom.example.com"
        fetch_strategy = FetchStrategy.DYNAMIC

        def list_postings(self) -> Iterator[ListingStub]:
            return iter([])

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

    adapter = CustomStrategyAdapter()
    assert adapter.fetch_strategy == FetchStrategy.DYNAMIC


def test_site_adapter_screenshot_selector_default_none() -> None:
    class ConcreteAdapter(SiteAdapter):
        site_id = "test_site"
        base_url = "http://test.example.com"

        def list_postings(self) -> Iterator[ListingStub]:
            return iter([])

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

    adapter = ConcreteAdapter()
    assert adapter.screenshot_selector is None


def test_site_adapter_screenshot_selector_override() -> None:
    class CustomSelectorAdapter(SiteAdapter):
        site_id = "custom_selector_site"
        base_url = "http://custom.example.com"
        screenshot_selector = "div.desc"

        def list_postings(self) -> Iterator[ListingStub]:
            return iter([])

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            return JobPosting(
                site_id=self.site_id,
                listing_id=stub.listing_id,
                source_url=stub.detail_url,
                title=stub.title,
            )

    adapter = CustomSelectorAdapter()
    assert adapter.screenshot_selector == "div.desc"


def test_all_registered_adapters_have_valid_screenshot_selector() -> None:
    from job_scraper.sites.registry import SITE_REGISTRY

    for site_id, adapter_class in SITE_REGISTRY.items():
        assert hasattr(adapter_class, "screenshot_selector"), f"{adapter_class} missing screenshot_selector"
        selector = adapter_class.screenshot_selector
        assert selector is None or isinstance(selector, str), (
            f"{adapter_class} screenshot_selector must be None or a string, "
            f"got {type(selector).__name__}"
        )
        if isinstance(selector, str):
            assert len(selector) > 0, f"{adapter_class} screenshot_selector must not be empty"


def test_screenshot_hide_selectors_default_and_tuple_for_all_adapters() -> None:
    from job_scraper.sites.registry import SITE_REGISTRY

    assert SiteAdapter.screenshot_hide_selectors == ()
    for adapter_class in SITE_REGISTRY.values():
        sel = adapter_class.screenshot_hide_selectors
        assert isinstance(sel, tuple), f"{adapter_class} hide selectors must be a tuple"
        assert all(isinstance(s, str) and s for s in sel)


# --- E16-S09: PostingGone and gone_check ---


def test_fetch_page_no_gone_check_static_old_behavior() -> None:
    """With gone_check=None, static fetch returns body as before."""
    class FakeResponse:
        body = b"<html>test</html>"
        status = 404

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        result = fetch_page(FetchStrategy.STATIC, "https://example.com")
        assert result == b"<html>test</html>"
        mock_get.assert_called_once_with("https://example.com")


def test_fetch_page_no_gone_check_stealth_old_behavior() -> None:
    """With gone_check=None, stealth fetch returns body as before."""
    class FakeResponse:
        body = b"<html>stealth test</html>"
        status = 404

    with patch("job_scraper.sites.base.StealthyFetcher.fetch") as mock_fetch:
        mock_fetch.return_value = FakeResponse()
        result = fetch_page(FetchStrategy.STEALTH, "https://example.com")
        assert result == b"<html>stealth test</html>"
        mock_fetch.assert_called_once_with("https://example.com", headless=True)


def test_fetch_page_gone_check_404_static_raises() -> None:
    """With gone_check, status 404 raises PostingGone with reason 'http 404'."""
    class FakeResponse:
        body = b"<html>not found</html>"
        status = 404

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123")
        with pytest.raises(PostingGone) as exc_info:
            fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert exc_info.value.url == "https://example.com/job/123"
        assert exc_info.value.reason == "http 404"
        assert str(exc_info.value) == "https://example.com/job/123: http 404"


def test_fetch_page_gone_check_404_stealth_raises() -> None:
    """With gone_check, status 404 raises PostingGone with stealth fetcher."""
    class FakeResponse:
        body = b"<html>not found</html>"
        status = 404

    with patch("job_scraper.sites.base.StealthyFetcher.fetch") as mock_fetch:
        mock_fetch.return_value = FakeResponse()
        check = GoneCheck("job-123")
        with pytest.raises(PostingGone) as exc_info:
            fetch_page(FetchStrategy.STEALTH, "https://example.com/job/123", gone_check=check)
        assert exc_info.value.reason == "http 404"


def test_fetch_page_gone_check_410_raises() -> None:
    """With gone_check, status 410 raises PostingGone."""
    class FakeResponse:
        body = b"<html>gone</html>"
        status = 410

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123")
        with pytest.raises(PostingGone) as exc_info:
            fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert exc_info.value.reason == "http 410"


def test_fetch_page_gone_check_200_no_redirect_returns_body() -> None:
    """With gone_check, status 200 with url=request URL returns body."""
    class FakeResponse:
        body = b"<html>job details</html>"
        status = 200
        url = "https://example.com/job/123"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123")
        result = fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert result == b"<html>job details</html>"


def test_fetch_page_gone_check_redirect_to_listing_raises() -> None:
    """With gone_check, 200 redirect to listing path raises."""
    class FakeResponse:
        body = b"<html>listing</html>"
        status = 200
        url = "https://example.com/jobs"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123", ("/jobs",))
        with pytest.raises(PostingGone) as exc_info:
            fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert "redirect to /jobs" in exc_info.value.reason


def test_fetch_page_gone_check_marker_in_title_raises() -> None:
    """With gone_check, title containing gone marker raises."""
    html = b"<html><title>Job Not Found</title><body></body></html>"

    class FakeResponse:
        body = html
        status = 200
        url = "https://example.com/job/123"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123", gone_markers=("job not found",))
        with pytest.raises(PostingGone) as exc_info:
            fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert "marker" in exc_info.value.reason


def test_fetch_page_gone_check_marker_in_h1_raises() -> None:
    """With gone_check, h1 containing gone marker raises."""
    html = b"<html><h1>Job Not Found</h1><body></body></html>"

    class FakeResponse:
        body = html
        status = 200
        url = "https://example.com/job/123"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123", gone_markers=("job not found",))
        with pytest.raises(PostingGone) as exc_info:
            fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert "marker" in exc_info.value.reason


def test_fetch_page_gone_check_marker_in_p_returns_body() -> None:
    """With gone_check, marker in <p> (not title/h1) does NOT raise."""
    html = b"<html><body><p>Job Not Found</p></body></html>"

    class FakeResponse:
        body = html
        status = 200
        url = "https://example.com/job/123"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123", gone_markers=("job not found",))
        result = fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert result == html


def test_fetch_page_gone_check_fake_without_status_url_returns_body() -> None:
    """With gone_check, a FakeResponse with only .body returns body (no status/url attrs)."""
    class FakeResponse:
        body = b"<html>test</html>"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123")
        result = fetch_page(FetchStrategy.STATIC, "https://example.com/job/123", gone_check=check)
        assert result == b"<html>test</html>"


def test_fetch_page_gone_check_not_forwarded_to_fetcher() -> None:
    """With gone_check, the parameter is NOT forwarded to the fetcher."""
    class FakeResponse:
        body = b"<html>test</html>"

    with patch("job_scraper.sites.base.Fetcher.get") as mock_get:
        mock_get.return_value = FakeResponse()
        check = GoneCheck("job-123")
        fetch_page(FetchStrategy.STATIC, "https://example.com", gone_check=check)
        # Verify the fetcher was called with just the URL, no gone_check param
        mock_get.assert_called_once_with("https://example.com")


def test_site_adapter_listing_paths_default() -> None:
    """SiteAdapter has listing_paths as empty tuple by default."""
    assert SiteAdapter.listing_paths == ()


def test_site_adapter_gone_markers_default() -> None:
    """SiteAdapter has gone_markers as empty tuple by default."""
    assert SiteAdapter.gone_markers == ()


def test_site_adapter_gone_check_classmethod() -> None:
    """SiteAdapter.gone_check() returns GoneCheck with default values."""
    check = SiteAdapter.gone_check()
    assert check == GoneCheck("", (), ())


def test_site_adapter_gone_check_with_listing_id() -> None:
    """SiteAdapter.gone_check(listing_id) includes listing_id."""
    check = SiteAdapter.gone_check("job-123")
    assert check == GoneCheck("job-123", (), ())


def test_site_adapter_subclass_gone_check() -> None:
    """Subclass with listing_paths and gone_markers includes them in gone_check()."""
    class TestAdapter(SiteAdapter):
        site_id = "test"
        base_url = "https://test.example.com"
        listing_paths = ("/jobs", "/listings")
        gone_markers = ("job not found", "page expired")

        def list_postings(self) -> Iterator[ListingStub]:
            return iter([])

        def parse_detail(self, stub: ListingStub, page: Any) -> JobPosting:
            raise NotImplementedError

    check = TestAdapter.gone_check("job-123")
    assert check == GoneCheck("job-123", ("/jobs", "/listings"), ("job not found", "page expired"))


def test_all_registered_adapters_have_tuple_listing_paths_and_gone_markers() -> None:
    """Every adapter in SITE_REGISTRY has tuple-typed listing_paths and gone_markers."""
    from job_scraper.sites.registry import SITE_REGISTRY

    for site_id, adapter_class in SITE_REGISTRY.items():
        listing_paths = adapter_class.listing_paths
        gone_markers = adapter_class.gone_markers
        assert isinstance(listing_paths, tuple), (
            f"{adapter_class} listing_paths must be a tuple, got {type(listing_paths).__name__}"
        )
        assert isinstance(gone_markers, tuple), (
            f"{adapter_class} gone_markers must be a tuple, got {type(gone_markers).__name__}"
        )
        assert all(isinstance(p, str) for p in listing_paths), (
            f"{adapter_class} listing_paths contains non-string values"
        )
        assert all(isinstance(m, str) for m in gone_markers), (
            f"{adapter_class} gone_markers contains non-string values"
        )
