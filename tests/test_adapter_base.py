from typing import Any, Iterator

import pytest

from job_scraper.core.models import JobPosting, ListingStub
from job_scraper.sites.base import FetchStrategy, SiteAdapter


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
