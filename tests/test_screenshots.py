import logging
import struct
from unittest.mock import patch

import pytest

from job_scraper.core.screenshots import browser_available, capture_element

needs_browser = pytest.mark.skipif(
    not browser_available(), reason="Chromium not installed"
)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def page_file(tmp_path):
    page = tmp_path / "page.html"
    page.write_text(
        '<nav style="height:500px">NAV</nav>'
        '<div id="job" style="height:300px;width:600px">Job text</div>'
    )
    return page


@pytest.mark.enable_socket
@needs_browser
def test_captures_only_element(tmp_path, page_file):
    out = tmp_path / "out.png"
    assert capture_element(page_file.as_uri(), "#job", str(out)) is True
    data = out.read_bytes()
    assert data.startswith(PNG_MAGIC)
    width, height = struct.unpack(">II", data[16:24])
    assert abs(height - 300) <= 2
    assert abs(width - 600) <= 2


@pytest.mark.enable_socket
@needs_browser
def test_missing_selector_returns_false(tmp_path, page_file):
    out = tmp_path / "out.png"
    assert capture_element(page_file.as_uri(), "#nope", str(out), timeout_ms=500) is False
    assert not out.exists()


@pytest.mark.enable_socket
@needs_browser
def test_missing_page_returns_false(tmp_path):
    out = tmp_path / "out.png"
    url = (tmp_path / "missing.html").as_uri()
    assert capture_element(url, "#job", str(out), timeout_ms=2000) is False
    assert not out.exists()


def test_never_raises_when_playwright_fails(tmp_path, caplog):
    out = tmp_path / "out.png"
    with patch(
        "job_scraper.core.screenshots.sync_playwright",
        side_effect=RuntimeError("boom"),
    ), caplog.at_level(logging.WARNING):
        assert capture_element("file:///x.html", "#a", str(out)) is False
    assert "file:///x.html" in caplog.text and "boom" in caplog.text


@pytest.mark.enable_socket
def test_browser_available_returns_bool():
    assert isinstance(browser_available(), bool)
