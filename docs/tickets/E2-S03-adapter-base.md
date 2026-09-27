# E2-S03: SiteAdapter base class, FetchStrategy enum, and empty registry

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends on `E1-S01`
(`JobPosting`, `ListingStub`).

## Goal

The contract every site adapter implements, and the lookup table the CLI
uses to find adapters by id. This story does NOT implement any real site —
just the shared base and an empty registry, so adapter stories (Epic 3) can
build against a stable interface in parallel.

## Context

Create: `job_scraper/sites/base.py`, `job_scraper/sites/registry.py`,
`tests/test_adapter_base.py`.

Import `JobPosting`, `ListingStub` from `job_scraper.core.models`.

```python
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
```

`page`'s type is `Any` for now — it will be a Scrapling response object
once real adapters (Epic 3) are wired up, but this base module has no
Scrapling dependency itself.

`job_scraper/sites/registry.py`:

```python
SITE_REGISTRY: dict[str, type[SiteAdapter]] = {}
```

(Deliberately empty — Epic 3 adapter stories each only create their own new
`sites/<name>.py` file; a single later story, `E3-S05`, adds the imports and
registrations here, avoiding every adapter story touching this same file.)

## Acceptance criteria

- `FetchStrategy` has exactly the three members shown, with those string
  values.
- `SiteAdapter` is abstract: instantiating a subclass that doesn't
  implement both `list_postings` and `parse_detail` raises `TypeError`.
- A minimal concrete subclass defined in the test file (with both methods
  implemented as trivial stubs) can be instantiated and its `fetch_strategy`
  defaults to `FetchStrategy.STATIC` when not overridden.
- `SITE_REGISTRY` exists in `job_scraper/sites/registry.py`, is an empty
  dict, and is typed `dict[str, type[SiteAdapter]]`.
- `tests/test_adapter_base.py` covers the abstract-instantiation-fails case
  and the default-fetch_strategy case.

## Definition of done

Per Appendix A.
