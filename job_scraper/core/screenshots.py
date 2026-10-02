"""Headless-Chromium element screenshots."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

_VIEWPORT = {"width": 1280, "height": 1600}


def browser_available() -> bool:
    """True iff plain-playwright Chromium's executable exists (no launch)."""
    try:
        with sync_playwright() as p:
            return bool(os.path.exists(p.chromium.executable_path))
    except Exception:
        return False


def capture_element(
    url: str,
    selector: str,
    out_path: str,
    *,
    stealth: bool = False,
    timeout_ms: int = 30000,
) -> bool:
    """Save a PNG of only the first element matching ``selector``.

    Never raises: on any failure logs a warning, removes a partial file and
    returns False.
    """
    try:
        if stealth:
            from patchright.sync_api import sync_playwright as launcher
        else:
            launcher = sync_playwright
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with launcher() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=_VIEWPORT)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_selector(selector, timeout=timeout_ms)
                page.locator(selector).first.screenshot(path=out_path)
            finally:
                browser.close()
        return True
    except Exception as exc:  # noqa: BLE001 - contract: never raise
        logger.warning("Screenshot of %s failed: %s", url, exc)
        try:
            Path(out_path).unlink(missing_ok=True)
        except OSError:
            pass
        return False
