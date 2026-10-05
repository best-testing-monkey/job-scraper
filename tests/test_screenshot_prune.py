"""Tests for screenshot_prune module."""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

import pytest

from job_scraper.core.screenshot_prune import prune_small_screenshots


def make_png(path: Path, width: int, height: int) -> None:
    """Build a minimal PNG file with given width and height.

    Writes magic + IHDR chunk with specified dimensions. The _png_height
    function only reads bytes 16:24, so we just need those to be valid.
    """
    data = bytearray(24)
    # PNG magic
    data[0:8] = b"\x89PNG\r\n\x1a\n"
    # IHDR width (bytes 16-19)
    data[16:20] = struct.pack(">I", width)
    # IHDR height (bytes 20-23)
    data[20:24] = struct.pack(">I", height)
    path.write_bytes(bytes(data))


def test_prune_basic(tmp_path):
    """Test that PNGs under threshold are moved and markdown is updated."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    # Create test PNGs with different heights
    make_png(screenshots / "hero-1-short.png", 800, 65)    # move
    make_png(screenshots / "hero-2-medium.png", 800, 99)   # move
    make_png(screenshots / "hero-3-ok.png", 800, 100)      # keep
    make_png(screenshots / "hero-4-tall.png", 800, 300)    # keep

    # Create markdown files
    for stem in ["hero-1-short", "hero-2-medium", "hero-3-ok", "hero-4-tall"]:
        md = jobs / f"{stem}.md"
        md.write_text(
            f"# Job\n\n- Source: http://example.com\n"
            f"- Screenshot: screenshots/{stem}.png\n\n## Description\n\nTest"
        )

    # Run prune
    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    # Check counters
    assert result["scanned"] == 4
    assert result["small"] == 2
    assert result["moved"] == 2
    assert result["markdown_updated"] == 2
    assert result["unreadable"] == 0
    assert result["skipped_exists"] == 0

    # Check files were moved
    assert not (screenshots / "hero-1-short.png").exists()
    assert not (screenshots / "hero-2-medium.png").exists()
    assert (move_to / "hero-1-short.png").exists()
    assert (move_to / "hero-2-medium.png").exists()

    # Check files that should stay are still there
    assert (screenshots / "hero-3-ok.png").exists()
    assert (screenshots / "hero-4-tall.png").exists()

    # Check markdown was updated for moved files
    md1 = (jobs / "hero-1-short.md").read_text()
    assert "- Screenshot:" not in md1
    md2 = (jobs / "hero-2-medium.md").read_text()
    assert "- Screenshot:" not in md2

    # Check markdown was NOT updated for kept files
    md3 = (jobs / "hero-3-ok.md").read_text()
    assert "- Screenshot:" in md3
    md4 = (jobs / "hero-4-tall.md").read_text()
    assert "- Screenshot:" in md4


def test_sites_filter(tmp_path):
    """Test that sites parameter filters which files are processed."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    # Create PNGs from different sites, all short
    make_png(screenshots / "hero-1-short.png", 800, 65)
    make_png(screenshots / "harveynash-1-short.png", 800, 30)

    # Create markdown files
    for stem in ["hero-1-short", "harveynash-1-short"]:
        md = jobs / f"{stem}.md"
        md.write_text(
            f"# Job\n\n- Source: http://example.com\n"
            f"- Screenshot: screenshots/{stem}.png\n\n## Description\n\nTest"
        )

    # Run prune for hero only
    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        sites=["hero"],
        move_to=str(move_to),
        dry_run=False,
    )

    # Only hero-1 should be moved
    assert result["small"] == 1  # Only hero-1 counted as small
    assert result["moved"] == 1
    assert result["markdown_updated"] == 1

    # hero-1 moved, harveynash-1 stays
    assert not (screenshots / "hero-1-short.png").exists()
    assert (screenshots / "harveynash-1-short.png").exists()
    assert (move_to / "hero-1-short.png").exists()


def test_dry_run(tmp_path):
    """Test that dry_run=True counts but doesn't move or edit."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    make_png(screenshots / "test-1-short.png", 800, 50)
    md = jobs / "test-1-short.md"
    md.write_text(
        "# Job\n\n- Source: http://example.com\n"
        "- Screenshot: screenshots/test-1-short.png\n\n## Description\n\nTest"
    )

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=True,
    )

    # Counters reflect dry run
    assert result["small"] == 1
    assert result["moved"] == 0
    assert result["markdown_updated"] == 0

    # File still exists in screenshots
    assert (screenshots / "test-1-short.png").exists()
    # No move_to directory created
    assert not move_to.exists()
    # Markdown unchanged
    assert "- Screenshot:" in md.read_text()


def test_missing_move_to_raises(tmp_path):
    """Test that move_to=None without dry_run raises ValueError."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    screenshots.mkdir()
    jobs.mkdir()

    make_png(screenshots / "test-1.png", 800, 50)

    with pytest.raises(ValueError, match="move_to is required unless dry_run"):
        prune_small_screenshots(
            str(screenshots),
            str(jobs),
            min_height=100,
            move_to=None,
            dry_run=False,
        )


def test_unreadable_file(tmp_path):
    """Test that unreadable files are counted and left in place."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    # Create a garbage file that's not a valid PNG
    (screenshots / "garbage.png").write_text("not a png")

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    assert result["scanned"] == 1
    assert result["unreadable"] == 1
    assert result["small"] == 0
    assert result["moved"] == 0

    # File stays in place
    assert (screenshots / "garbage.png").exists()


def test_skipped_exists(tmp_path):
    """Test that pre-existing target files are counted and source left in place."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()
    move_to.mkdir(parents=True)

    # Create PNG that's too short
    make_png(screenshots / "test-1-short.png", 800, 50)

    # Create a file with the same name in target
    (move_to / "test-1-short.png").write_text("already here")

    # Create markdown
    md = jobs / "test-1-short.md"
    md.write_text(
        "# Job\n\n- Source: http://example.com\n"
        "- Screenshot: screenshots/test-1-short.png\n\n## Description\n\nTest"
    )

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    assert result["small"] == 1
    assert result["moved"] == 0
    assert result["markdown_updated"] == 0
    assert result["skipped_exists"] == 1

    # Source PNG still in screenshots
    assert (screenshots / "test-1-short.png").exists()

    # Target file unchanged
    assert (move_to / "test-1-short.png").read_text() == "already here"

    # Markdown still has screenshot line
    assert "- Screenshot:" in md.read_text()


def test_idempotent(tmp_path):
    """Test that running twice changes nothing on second run."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    make_png(screenshots / "test-1-short.png", 800, 50)
    md = jobs / "test-1-short.md"
    md.write_text(
        "# Job\n\n- Source: http://example.com\n"
        "- Screenshot: screenshots/test-1-short.png\n\n## Description\n\nTest"
    )

    # First run
    result1 = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    assert result1["moved"] == 1
    assert result1["markdown_updated"] == 1

    # Second run
    result2 = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    # Nothing changed
    assert result2["moved"] == 0
    assert result2["markdown_updated"] == 0
    assert result2["small"] == 0  # PNG not in screenshots anymore


def test_png_without_markdown(tmp_path):
    """Test that PNG with no matching markdown still moves."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    # Create short PNG but no markdown
    make_png(screenshots / "test-1-short.png", 800, 50)

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    assert result["small"] == 1
    assert result["moved"] == 1
    assert result["markdown_updated"] == 0  # No markdown to update

    # PNG moved
    assert not (screenshots / "test-1-short.png").exists()
    assert (move_to / "test-1-short.png").exists()


def test_multiple_sites_filter(tmp_path):
    """Test filtering with multiple sites."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    # Create short PNGs from different sites
    make_png(screenshots / "hero-1-short.png", 800, 50)
    make_png(screenshots / "mywork-1-short.png", 800, 50)
    make_png(screenshots / "harveynash-1-short.png", 800, 50)

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        sites=["hero", "mywork"],
        move_to=str(move_to),
        dry_run=False,
    )

    # Only hero and mywork should be counted as small
    assert result["small"] == 2
    assert result["moved"] == 2

    # hero and mywork moved, harveynash stays
    assert not (screenshots / "hero-1-short.png").exists()
    assert not (screenshots / "mywork-1-short.png").exists()
    assert (screenshots / "harveynash-1-short.png").exists()


def test_empty_sites_list(tmp_path):
    """Test that empty sites list processes all files (like None)."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    make_png(screenshots / "hero-1-short.png", 800, 50)
    make_png(screenshots / "harveynash-1-short.png", 800, 50)

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        sites=[],  # Empty list, should process all
        move_to=str(move_to),
        dry_run=False,
    )

    # Both should be processed
    assert result["small"] == 2
    assert result["moved"] == 2


def test_return_keys(tmp_path):
    """Test that all required keys are in the returned dict."""
    screenshots = tmp_path / "screenshots"
    jobs = tmp_path / "jobs"
    move_to = tmp_path / "pruned"
    screenshots.mkdir()
    jobs.mkdir()

    result = prune_small_screenshots(
        str(screenshots),
        str(jobs),
        min_height=100,
        move_to=str(move_to),
        dry_run=False,
    )

    required_keys = {"scanned", "small", "moved", "markdown_updated", "unreadable", "skipped_exists"}
    assert set(result.keys()) == required_keys
