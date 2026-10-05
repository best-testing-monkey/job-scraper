import re
from pathlib import Path

import pytest

from job_scraper.core.markdown_export import (
    filename_for,
    md_path_for,
    render,
    screenshot_relpath,
    set_screenshot_line,
    set_stale_line,
    slugify,
    stem_for,
    write,
)
from job_scraper.core.models import JobPosting


class TestSlugify:
    def test_slugify_with_special_chars(self) -> None:
        result = slugify("Spoed | Test Automation Engineer | Overheid")
        assert result == "spoed-test-automation-engineer-overheid"
        assert not result.startswith("-")
        assert not result.endswith("-")
        assert "--" not in result

    def test_slugify_lowercase(self) -> None:
        result = slugify("HELLO WORLD")
        assert result == "hello-world"

    def test_slugify_multiple_spaces(self) -> None:
        result = slugify("Hello   World")
        assert result == "hello-world"

    def test_slugify_parentheses(self) -> None:
        result = slugify("Senior Tester (RVO)!")
        assert result == "senior-tester-rvo"

    def test_slugify_no_leading_trailing_hyphens(self) -> None:
        result = slugify("--test--")
        assert not result.startswith("-")
        assert not result.endswith("-")


class TestFilenameFor:
    def test_filename_for_freelapp_tester(self) -> None:
        posting = JobPosting(
            site_id="freelapp",
            listing_id="508877",
            source_url="https://freelapp.nl/freelance-opdracht/tester/508877",
            title="Tester (RVO, remote in Nederland)",
            client="Rijksdienst voor Ondernemend Nederland (RVO)",
        )
        result = filename_for(posting)
        assert result == "freelapp-508877-tester-rvo-remote-in-nederland.md"

    def test_filename_for_site_listing_prefix_exact(self) -> None:
        posting = JobPosting(
            site_id="example-site",
            listing_id="12345",
            source_url="https://example.com/job/12345",
            title="Test Job",
        )
        result = filename_for(posting)
        assert result.startswith("example-site-12345-")
        assert result.endswith(".md")


class TestStemFor:
    def test_stem_for_basic(self) -> None:
        posting = JobPosting(
            site_id="freelapp",
            listing_id="508877",
            source_url="https://freelapp.nl/freelance-opdracht/tester/508877",
            title="Tester (RVO, remote in Nederland)",
            client="Rijksdienst voor Ondernemend Nederland (RVO)",
        )
        result = stem_for(posting)
        assert result == "freelapp-508877-tester-rvo-remote-in-nederland"
        assert not result.endswith(".md")

    def test_stem_for_no_extension(self) -> None:
        posting = JobPosting(
            site_id="example",
            listing_id="123",
            source_url="https://example.com",
            title="Test Job",
        )
        result = stem_for(posting)
        assert not result.endswith(".md")


class TestScreenshotRelpath:
    def test_screenshot_relpath_basic(self) -> None:
        result = screenshot_relpath("freelapp-508877-tester-rvo")
        assert result == "screenshots/freelapp-508877-tester-rvo.png"

    def test_screenshot_relpath_format(self) -> None:
        stem = "example-123-test-job"
        result = screenshot_relpath(stem)
        assert result.startswith("screenshots/")
        assert result.endswith(".png")
        assert stem in result


class TestRender:
    def test_render_with_all_fields(self) -> None:
        posting = JobPosting(
            site_id="freelapp",
            listing_id="508877",
            source_url="https://freelapp.nl/freelance-opdracht/tester/508877",
            title="Tester (RVO, remote in Nederland)",
            client="Rijksdienst voor Ondernemend Nederland (RVO)",
            category="Test Engineer (IT & technologie)",
            level="Senior",
            status="Active",
            location="Nederland, remote",
            hours="36 uur/week",
            rate="not stated",
            duration="tot 07-08-2030",
            posted_date="2026-08-07 08:08:59",
            experience="5+ jaar",
            skills=["Scrum", "SAFe", "Agile"],
            description="Test description here.",
            scrape_note="Some scrape note.",
            extra_fields={"Custom Field": "Custom Value"},
        )
        result = render(posting)

        assert "# Tester (RVO, remote in Nederland)" in result
        assert "- Source: https://freelapp.nl/freelance-opdracht/tester/508877" in result
        assert "- Client: Rijksdienst voor Ondernemend Nederland (RVO)" in result
        assert "- Category: Test Engineer (IT & technologie)" in result
        assert "- Level: Senior" in result
        assert "- Status: Active" in result
        assert "- Location: Nederland, remote" in result
        assert "- Hours: 36 uur/week" in result
        assert "- Rate: not stated" in result
        assert "- Duration: tot 07-08-2030" in result
        assert "- Posted: 2026-08-07 08:08:59" in result
        assert "- Experience: 5+ jaar" in result
        assert "- Skills: Scrum, SAFe, Agile" in result
        assert "- Custom Field: Custom Value" in result
        assert "\n## Description\n" in result
        assert "Test description here." in result
        assert "\n## Scrape note\n" in result
        assert "Some scrape note." in result

    def test_render_minimal_fields(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com/job/123",
            title="Test Job",
            description="Test description.",
        )
        result = render(posting)

        assert "# Test Job" in result
        assert "- Source: https://test.com/job/123" in result
        assert "\n## Description\n" in result
        assert "Test description." in result
        assert "## Scrape note" not in result
        assert "- Client:" not in result
        assert "- Category:" not in result
        assert "- Level:" not in result
        assert "- Status:" not in result
        assert "- Location:" not in result
        assert "- Hours:" not in result
        assert "- Rate:" not in result
        assert "- Duration:" not in result
        assert "- Posted:" not in result
        assert "- Experience:" not in result
        assert "- Skills:" not in result

    def test_render_field_order(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            client="Client",
            category="Category",
            level="Level",
            status="Status",
            location="Location",
            hours="Hours",
            rate="Rate",
            duration="Duration",
            posted_date="Posted",
            experience="Experience",
            skills=["Skill1"],
            description="Desc",
            extra_fields={"Extra": "Value"},
        )
        result = render(posting)
        lines = result.split("\n")

        source_idx = next(i for i, line in enumerate(lines) if "Source:" in line)
        client_idx = next(i for i, line in enumerate(lines) if "Client:" in line)
        category_idx = next(i for i, line in enumerate(lines) if "Category:" in line)
        level_idx = next(i for i, line in enumerate(lines) if "Level:" in line)
        status_idx = next(i for i, line in enumerate(lines) if "Status:" in line)
        location_idx = next(i for i, line in enumerate(lines) if "Location:" in line)
        hours_idx = next(i for i, line in enumerate(lines) if "Hours:" in line)
        rate_idx = next(i for i, line in enumerate(lines) if "Rate:" in line)
        duration_idx = next(i for i, line in enumerate(lines) if "Duration:" in line)
        posted_idx = next(i for i, line in enumerate(lines) if "Posted:" in line)
        experience_idx = next(i for i, line in enumerate(lines) if "Experience:" in line)
        skills_idx = next(i for i, line in enumerate(lines) if "Skills:" in line)
        extra_idx = next(i for i, line in enumerate(lines) if "Extra:" in line)

        assert (
            source_idx
            < client_idx
            < category_idx
            < level_idx
            < status_idx
            < location_idx
            < hours_idx
            < rate_idx
            < duration_idx
            < posted_idx
            < experience_idx
            < skills_idx
            < extra_idx
        )

    def test_render_empty_description(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="",
        )
        result = render(posting)
        assert "## Description" in result

    def test_render_skip_none_fields(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            client=None,
            description="Test",
        )
        result = render(posting)
        assert "- Client:" not in result

    def test_render_skip_empty_string_fields(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            client="",
            description="Test",
        )
        result = render(posting)
        assert "- Client:" not in result

    def test_render_empty_skills_list(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            skills=[],
            description="Test",
        )
        result = render(posting)
        assert "- Skills:" not in result

    def test_render_empty_extra_fields(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            extra_fields={},
            description="Test",
        )
        result = render(posting)
        assert "- " in result

    def test_render_no_scrape_note_when_none(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            scrape_note=None,
            description="Test",
        )
        result = render(posting)
        assert "## Scrape note" not in result

    def test_render_no_scrape_note_when_empty(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            scrape_note="",
            description="Test",
        )
        result = render(posting)
        assert "## Scrape note" not in result

    def test_render_with_screenshot(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, screenshot="screenshots/test-123-test.png")
        assert "- Screenshot: screenshots/test-123-test.png" in result

    def test_render_without_screenshot(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, screenshot=None)
        assert "- Screenshot:" not in result

    def test_render_empty_screenshot_string(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, screenshot="")
        assert "- Screenshot:" not in result

    def test_render_screenshot_position_after_extra_fields(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
            extra_fields={"Custom Field": "Custom Value"},
        )
        result = render(posting, screenshot="screenshots/test.png")
        lines = result.split("\n")

        extra_idx = next(i for i, line in enumerate(lines) if "Custom Field:" in line)
        screenshot_idx = next(i for i, line in enumerate(lines) if "Screenshot:" in line)
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")

        assert extra_idx < screenshot_idx < description_idx

    def test_render_screenshot_before_description(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, screenshot="screenshots/test.png")
        lines = result.split("\n")

        screenshot_idx = next(i for i, line in enumerate(lines) if "Screenshot:" in line)
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")

        # Should be: screenshot, blank line, description
        assert lines[screenshot_idx].startswith("- Screenshot:")
        assert lines[screenshot_idx + 1] == ""
        assert lines[screenshot_idx + 2] == "## Description"

    def test_render_byte_identical_without_screenshot(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result_without = render(posting)
        result_with_none = render(posting, screenshot=None)

        assert result_without == result_with_none

    def test_render_app_regex_matches_screenshot(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, screenshot="screenshots/x.png")

        # App regex from ticket
        app_regex = r"^- (\w[\w ]*):\s*(.+)$"

        for line in result.split("\n"):
            if "Screenshot:" in line:
                match = re.match(app_regex, line)
                assert match is not None
                assert match.group(1) == "Screenshot"
                assert match.group(2) == "screenshots/x.png"


class TestWrite:
    def test_write_creates_directory(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )

        result = write(posting, str(jobs_dir))

        assert jobs_dir.exists()
        assert Path(result).exists()

    def test_write_file_content(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            client="Test Client",
            description="Test description.",
        )

        result = write(posting, str(jobs_dir))
        file_path = Path(result)
        content = file_path.read_text()

        assert content == render(posting)

    def test_write_returns_full_path(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        posting = JobPosting(
            site_id="freelapp",
            listing_id="508877",
            source_url="https://freelapp.nl/freelance-opdracht/tester/508877",
            title="Tester (RVO, remote in Nederland)",
            description="Test.",
        )

        result = write(posting, str(jobs_dir))

        assert result.endswith("freelapp-508877-tester-rvo-remote-in-nederland.md")
        assert str(jobs_dir) in result

    def test_write_existing_directory(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        jobs_dir.mkdir(parents=True)
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )

        result = write(posting, str(jobs_dir))

        assert Path(result).exists()
        assert jobs_dir.exists()

    def test_write_with_screenshot(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )

        result = write(posting, str(jobs_dir), screenshot="screenshots/test.png")
        file_path = Path(result)
        content = file_path.read_text()

        assert "- Screenshot: screenshots/test.png" in content
        assert content == render(posting, screenshot="screenshots/test.png")


class TestSetScreenshotLine:
    def test_set_screenshot_line_insert_new(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        result = set_screenshot_line(str(md_path), "screenshots/test.png")

        assert result is True
        content = md_path.read_text()
        assert "- Screenshot: screenshots/test.png" in content

    def test_set_screenshot_line_replace_existing(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting, screenshot="screenshots/old.png"))

        result = set_screenshot_line(str(md_path), "screenshots/new.png")

        assert result is True
        content = md_path.read_text()
        assert "- Screenshot: screenshots/new.png" in content
        assert "screenshots/old.png" not in content

    def test_set_screenshot_line_idempotent(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting, screenshot="screenshots/test.png"))

        # First call should return False because it's already there
        result = set_screenshot_line(str(md_path), "screenshots/test.png")
        assert result is False

        content = md_path.read_text()
        assert "- Screenshot: screenshots/test.png" in content

    def test_set_screenshot_line_insert_position(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
            extra_fields={"Custom": "Value"},
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        set_screenshot_line(str(md_path), "screenshots/test.png")

        content = md_path.read_text()
        lines = content.split("\n")

        custom_idx = next(i for i, line in enumerate(lines) if "Custom:" in line)
        screenshot_idx = next(i for i, line in enumerate(lines) if "Screenshot:" in line)
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")

        # Screenshot should be after custom field and before description
        assert custom_idx < screenshot_idx < description_idx

    def test_set_screenshot_line_preserves_description(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description text here.",
            scrape_note="Scrape note here.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        set_screenshot_line(str(md_path), "screenshots/test.png")

        content = md_path.read_text()
        assert "Test description text here." in content
        assert "Scrape note here." in content

    def test_set_screenshot_line_app_regex_match(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        set_screenshot_line(str(md_path), "screenshots/test-123-test.png")

        content = md_path.read_text()
        app_regex = r"^- (\w[\w ]*):\s*(.+)$"

        for line in content.split("\n"):
            if "Screenshot:" in line:
                match = re.match(app_regex, line)
                assert match is not None
                assert match.group(1) == "Screenshot"
                assert match.group(2) == "screenshots/test-123-test.png"


class TestMdPathFor:
    def test_md_path_for_basic(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test.",
        )
        result = md_path_for("/jobs", "test", "123", "Test Job")
        expected = Path("/jobs") / filename_for(posting)

        assert result == expected

    def test_md_path_for_slugify_applied(self) -> None:
        result = md_path_for("/jobs", "freelapp", "508877", "Tester (RVO, remote in Nederland)")
        assert result == Path("/jobs/freelapp-508877-tester-rvo-remote-in-nederland.md")

    def test_md_path_for_matches_filename_for(self) -> None:
        posting = JobPosting(
            site_id="example-site",
            listing_id="12345",
            source_url="https://example.com/job/12345",
            title="Senior Developer",
            description="Test.",
        )
        md_path_result = md_path_for("/jobs", posting.site_id, posting.listing_id, posting.title)
        filename_result = filename_for(posting)

        assert str(md_path_result) == f"/jobs/{filename_result}"


class TestRenderWithStaleSince:
    def test_render_with_stale_since(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, stale_since="2026-10-01")
        assert "- Stale since: 2026-10-01" in result

    def test_render_without_stale_since(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, stale_since=None)
        assert "- Stale since:" not in result

    def test_render_empty_stale_since(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, stale_since="")
        assert "- Stale since:" not in result

    def test_render_stale_since_after_screenshot(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, screenshot="screenshots/test.png", stale_since="2026-10-01")
        lines = result.split("\n")

        screenshot_idx = next(i for i, line in enumerate(lines) if "Screenshot:" in line)
        stale_idx = next(i for i, line in enumerate(lines) if "Stale since:" in line)
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")

        assert screenshot_idx < stale_idx < description_idx

    def test_render_stale_since_after_extra_fields_no_screenshot(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
            extra_fields={"Custom": "Value"},
        )
        result = render(posting, stale_since="2026-10-01")
        lines = result.split("\n")

        custom_idx = next(i for i, line in enumerate(lines) if "Custom:" in line)
        stale_idx = next(i for i, line in enumerate(lines) if "Stale since:" in line)
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")

        assert custom_idx < stale_idx < description_idx

    def test_render_byte_identical_without_stale_since(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result_without = render(posting)
        result_with_none = render(posting, stale_since=None)

        assert result_without == result_with_none

    def test_render_stale_since_app_regex(self) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test",
            description="Test",
        )
        result = render(posting, stale_since="2026-10-05")
        app_regex = r"^- (\w[\w ]*):\s*(.+)$"

        for line in result.split("\n"):
            if "Stale since:" in line:
                match = re.match(app_regex, line)
                assert match is not None
                assert match.group(1) == "Stale since"
                assert match.group(2) == "2026-10-05"


class TestWriteWithStaleSince:
    def test_write_with_stale_since(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )

        result = write(posting, str(jobs_dir), stale_since="2026-10-01")
        file_path = Path(result)
        content = file_path.read_text()

        assert "- Stale since: 2026-10-01" in content
        assert content == render(posting, stale_since="2026-10-01")

    def test_write_stale_since_passed_to_render(self, tmp_path: Path) -> None:
        jobs_dir = tmp_path / "jobs"
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )

        result = write(posting, str(jobs_dir), screenshot="screenshots/test.png", stale_since="2026-10-01")
        file_path = Path(result)
        content = file_path.read_text()

        assert content == render(posting, screenshot="screenshots/test.png", stale_since="2026-10-01")


class TestSetStaleLine:
    def test_set_stale_line_insert_new(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        result = set_stale_line(str(md_path), "2026-10-01")

        assert result is True
        content = md_path.read_text()
        assert "- Stale since: 2026-10-01" in content

    def test_set_stale_line_replace_existing(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting, stale_since="2026-10-01"))

        result = set_stale_line(str(md_path), "2026-10-02")

        assert result is True
        content = md_path.read_text()
        assert "- Stale since: 2026-10-02" in content
        assert "2026-10-01" not in content

    def test_set_stale_line_remove(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting, stale_since="2026-10-01"))

        result = set_stale_line(str(md_path), None)

        assert result is True
        content = md_path.read_text()
        assert "- Stale since:" not in content

    def test_set_stale_line_remove_when_absent(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        result = set_stale_line(str(md_path), None)

        assert result is False

    def test_set_stale_line_idempotent_second_call(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting, stale_since="2026-10-01"))

        # Second call should return False
        result = set_stale_line(str(md_path), "2026-10-01")

        assert result is False

    def test_set_stale_line_missing_file(self, tmp_path: Path) -> None:
        md_path = tmp_path / "nonexistent.md"

        result = set_stale_line(str(md_path), "2026-10-01")

        assert result is False

    def test_set_stale_line_bad_format_raises_error(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        with pytest.raises(ValueError):
            set_stale_line(str(md_path), "2026/10/01")

        with pytest.raises(ValueError):
            set_stale_line(str(md_path), "not-a-date")

    def test_set_stale_line_description_lookalike_untouched(self, tmp_path: Path) -> None:
        """Test that a line in the description that looks like '- Stale since: ...' is not touched."""
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Some text.\n- Stale since: 2020-01-01\nMore text here.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        result = set_stale_line(str(md_path), "2026-10-01")

        assert result is True
        content = md_path.read_text()
        # Check that the description's lookalike line is still there
        assert "- Stale since: 2020-01-01" in content
        # Check that we have the new line in the header
        lines = content.split("\n")
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")
        # Find the bullet line in the header section
        bullet_found = False
        for i in range(0, description_idx):
            if lines[i] == "- Stale since: 2026-10-01":
                bullet_found = True
                break
        assert bullet_found

    def test_set_stale_line_with_both_screenshot_and_stale(self, tmp_path: Path) -> None:
        """Test that a file with both screenshot and stale_since keeps both after operations."""
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting, screenshot="screenshots/test.png", stale_since="2026-10-01"))

        # Call set_screenshot_line - should not affect stale line
        set_screenshot_line(str(md_path), "screenshots/new.png")

        content = md_path.read_text()
        assert "- Screenshot: screenshots/new.png" in content
        assert "- Stale since: 2026-10-01" in content

        # Call set_stale_line - should not affect screenshot
        set_stale_line(str(md_path), "2026-10-02")

        content = md_path.read_text()
        assert "- Screenshot: screenshots/new.png" in content
        assert "- Stale since: 2026-10-02" in content

    def test_set_stale_line_insert_position(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
            extra_fields={"Custom": "Value"},
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        set_stale_line(str(md_path), "2026-10-01")

        content = md_path.read_text()
        lines = content.split("\n")

        custom_idx = next(i for i, line in enumerate(lines) if "Custom:" in line)
        stale_idx = next(i for i, line in enumerate(lines) if "Stale since:" in line)
        description_idx = next(i for i, line in enumerate(lines) if line == "## Description")

        # Stale should be after custom field and before description
        assert custom_idx < stale_idx < description_idx

    def test_set_stale_line_preserves_description(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description text here.",
            scrape_note="Scrape note here.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        set_stale_line(str(md_path), "2026-10-01")

        content = md_path.read_text()
        assert "Test description text here." in content
        assert "Scrape note here." in content

    def test_set_stale_line_app_regex_match(self, tmp_path: Path) -> None:
        posting = JobPosting(
            site_id="test",
            listing_id="123",
            source_url="https://test.com",
            title="Test Job",
            description="Test description.",
        )
        md_path = tmp_path / "test.md"
        md_path.write_text(render(posting))

        set_stale_line(str(md_path), "2026-10-05")

        content = md_path.read_text()
        app_regex = r"^- (\w[\w ]*):\s*(.+)$"

        for line in content.split("\n"):
            if "Stale since:" in line:
                match = re.match(app_regex, line)
                assert match is not None
                assert match.group(1) == "Stale since"
                assert match.group(2) == "2026-10-05"
