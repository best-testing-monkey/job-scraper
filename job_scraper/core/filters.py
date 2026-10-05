import re
from job_scraper.core.db import JobRepository
from job_scraper.core.models import JobPosting


EXCLUSION_KEYWORDS = (
    "geen zzp",
    "zzp niet toegestaan",
    "enkel detachering",
    "in loondienst",
)


def is_excluded(posting: JobPosting) -> bool:
    """Case-insensitive substring match of any EXCLUSION_KEYWORDS entry
    against posting.description. Returns True if the posting should be
    dropped (not stored, not exported)."""
    description_lower = posting.description.lower()
    return any(keyword in description_lower for keyword in EXCLUSION_KEYWORDS)


def apply_dedup(posting: JobPosting, repo: JobRepository) -> tuple[JobPosting, int | None]:
    """Normalizes posting.title/client/location (lowercase, strip, collapse
    whitespace) and calls repo.find_duplicate(...) with the normalized
    values. If a match is found, returns a tuple of posting and the matching
    row's id; if no match, returns (posting, None)."""
    normalized_title = _normalize_string(posting.title)
    normalized_client = _normalize_string(posting.client) if posting.client else None
    normalized_location = _normalize_string(posting.location) if posting.location else None

    duplicate_id = repo.find_duplicate(
        normalized_title,
        normalized_client,
        normalized_location,
        site_id=posting.site_id,
        listing_id=posting.listing_id,
    )

    return (posting, duplicate_id)


def _normalize_string(s: str) -> str:
    """Normalize a string: lowercase and collapse multiple spaces."""
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s
