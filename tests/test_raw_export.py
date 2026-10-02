from pathlib import Path

from job_scraper.core.models import JobPosting
from job_scraper.core.raw_export import filename_for, write


def make_posting() -> JobPosting:
    return JobPosting(
        site_id="wearedevelopers",
        listing_id="123",
        source_url="https://example.com/123",
        title="Senior Tester (RVO)!",
    )


def test_filename_for() -> None:
    assert filename_for(make_posting(), "html") == "wearedevelopers-123-senior-tester-rvo.html"


def test_write_creates_site_subdirectory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    write(make_posting(), b"<html></html>", str(raw_dir))

    assert (raw_dir / "wearedevelopers").is_dir()


def test_write_file_content(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    path = write(make_posting(), b"<html>hello</html>", str(raw_dir))

    assert Path(path).read_bytes() == b"<html>hello</html>"


def test_write_returns_full_path(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    path = write(make_posting(), b"data", str(raw_dir))

    assert path == str(raw_dir / "wearedevelopers" / "wearedevelopers-123-senior-tester-rvo.html")


def test_write_custom_extension(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    path = write(make_posting(), b'{"a": 1}', str(raw_dir), ext="json")

    assert path.endswith(".json")
