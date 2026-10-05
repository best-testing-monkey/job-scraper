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


_OVERLAY = (
    '<div id="CybotCookiebotDialog" style="position:fixed;inset:0;background:red"></div>'
)
_JOB_TEXT = '<p style="height:100px;margin:0;background:#00f">Job text</p>'
_FORM = '<div class="contact-info" style="height:150px;background:#0f0">Apply</div>'


@pytest.mark.enable_socket
@needs_browser
def test_hide_selectors_hide_overlay_and_form(tmp_path):
    import zlib

    full = tmp_path / "full.html"
    full.write_text(
        f'<body style="overflow:hidden">{_OVERLAY}'
        f'<div id="job" style="width:600px">{_JOB_TEXT}{_FORM}</div></body>'
    )
    plain = tmp_path / "plain.html"
    plain.write_text(f'<div id="job" style="width:600px">{_JOB_TEXT}</div>')
    out1, out2 = tmp_path / "o1.png", tmp_path / "o2.png"
    assert capture_element(
        full.as_uri(), "#job", str(out1), hide_selectors=("div.contact-info",)
    )
    assert capture_element(plain.as_uri(), "#job", str(out2))
    h1 = struct.unpack(">II", out1.read_bytes()[16:24])[1]
    h2 = struct.unpack(">II", out2.read_bytes()[16:24])[1]
    assert abs(h1 - h2) <= 2
    # no pure-red pixel anywhere: decode the PNG (8-bit RGB/RGBA, non-interlaced)
    data = out1.read_bytes()
    width, height, depth, ctype = struct.unpack(">IIBB", data[16:26])
    assert depth == 8 and ctype in (2, 6)
    bpp = 3 if ctype == 2 else 4
    idat, pos = b"", 8
    while pos < len(data):
        n, typ = struct.unpack(">I4s", data[pos : pos + 8])
        if typ == b"IDAT":
            idat += data[pos + 8 : pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = width * bpp
    prev = bytearray(stride)
    for y in range(height):
        row = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        ft = raw[y * (stride + 1)]
        for i in range(stride):
            a = row[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                row[i] = (row[i] + a) & 255
            elif ft == 2:
                row[i] = (row[i] + b) & 255
            elif ft == 3:
                row[i] = (row[i] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                row[i] = (row[i] + pr) & 255
        prev = row
        for x in range(width):
            r, g, bl = row[x * bpp : x * bpp + 3]
            assert not (r > 200 and g < 60 and bl < 60), "red overlay pixel found"


_PRE_ACTION_PAGE = (
    '<div id="job"><p>short</p>'
    "<button id=\"more\" onclick=\"document.getElementById('full').style.display='block';"
    'this.remove()">Show more</button>'
    '<div id="full" style="display:none;height:400px">full text</div></div>'
)


def _png_height(path):
    return struct.unpack(">II", path.read_bytes()[16:24])[1]


@pytest.mark.enable_socket
@needs_browser
def test_pre_actions_click_expands_content(tmp_path):
    page = tmp_path / "pre.html"
    page.write_text(_PRE_ACTION_PAGE)
    out1, out2 = tmp_path / "plain.png", tmp_path / "clicked.png"
    assert capture_element(page.as_uri(), "#job", str(out1))
    assert capture_element(
        page.as_uri(), "#job", str(out2), pre_actions=("button#more",)
    )
    assert _png_height(out2) >= _png_height(out1) + 350  # +400px block minus the removed button


@pytest.mark.enable_socket
@needs_browser
def test_missing_pre_action_does_not_fail_capture(tmp_path):
    page = tmp_path / "pre.html"
    page.write_text(_PRE_ACTION_PAGE)
    out = tmp_path / "out.png"
    assert capture_element(
        page.as_uri(), "#job", str(out), pre_actions=("button#does-not-exist",)
    ) is True
    assert out.exists()


def test_adapters_default_screenshot_pre_actions_empty():
    from job_scraper.sites.registry import SITE_REGISTRY

    for cls in SITE_REGISTRY.values():
        assert isinstance(cls.screenshot_pre_actions, tuple)
        assert cls.screenshot_pre_actions == ()
