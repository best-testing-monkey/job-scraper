from pathlib import Path

from job_scraper.core.markdown_export import slugify
from job_scraper.core.models import JobPosting


def filename_for(posting: JobPosting, ext: str) -> str:
    """f"{posting.site_id}-{posting.listing_id}-{slugify(posting.title)}.{ext}" """
    return f"{posting.site_id}-{posting.listing_id}-{slugify(posting.title)}.{ext}"


def write(posting: JobPosting, page: bytes, raw_dir: str, ext: str = "html") -> str:
    """Ensures raw_dir/{site_id}/ exists, writes the raw fetched page bytes
    to raw_dir/{site_id}/filename_for(posting, ext), returns the full path
    written. Kept alongside (not instead of) the parsed markdown so future
    fields can be re-extracted by reprocessing what's on disk, without a
    new web request."""
    site_dir = Path(raw_dir) / posting.site_id
    site_dir.mkdir(parents=True, exist_ok=True)

    file_path = site_dir / filename_for(posting, ext)
    file_path.write_bytes(page)

    return str(file_path)
