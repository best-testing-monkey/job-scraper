"""Headless-Chromium element screenshots."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from pathlib import Path

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

_VIEWPORT = {"width": 1280, "height": 1600}

GENERIC_HIDE_SELECTORS: tuple[str, ...] = (
    "#CybotCookiebotDialog",
    "#cookieyes-banner",
    "#onetrust-banner-sdk",
    ".cookie-banner",
    '[id*="cookie-consent" i]',
    '[class*="cookie-consent" i]',
)


def browser_available() -> bool:
    """True iff plain-playwright Chromium's executable exists (no launch)."""
    try:
        with sync_playwright() as p:
            return bool(os.path.exists(p.chromium.executable_path))
    except Exception:
        return False


def _is_challenge(response, title: str) -> bool:
    """True iff the response is a bot-wall challenge page (detect and skip only)."""
    if response is None:
        return False
    if response.headers.get("cf-mitigated") == "challenge":
        return True
    return response.status in (403, 503) and "just a moment" in title.lower()


def _screenshot_with_retry(page, selector, out_path, timeout_ms):
    """wait_for_selector + element screenshot, retried once if the element detached."""
    for attempt in (1, 2):
        try:
            page.wait_for_selector(selector, timeout=timeout_ms)
            page.locator(selector).first.screenshot(path=out_path)
            return
        except Exception as exc:  # noqa: BLE001 - only detach errors retry
            msg = str(exc).lower()
            if attempt == 2 or not ("not attached" in msg or "detached" in msg):
                raise
            page.wait_for_timeout(500)


def capture_element(
    url: str,
    selector: str,
    out_path: str,
    *,
    stealth: bool = False,
    timeout_ms: int = 30000,
    hide_selectors: Sequence[str] = (),
    pre_actions: Sequence[str] = (),
    skip_selectors: Sequence[str] = (),
) -> bool | None:
    """Save a PNG of only the first element matching ``selector``.

    Elements matching GENERIC_HIDE_SELECTORS + ``hide_selectors`` are hidden
    first (display: none) and page scrolling is unlocked. Each selector in
    ``pre_actions`` is then clicked once (if present and visible).

    Returns True when saved, False on failure, None when skipped on purpose
    (bot-challenge page, or any ``skip_selectors`` match = gate/teaser page);
    a skip writes no file.

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
                response = page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout_ms
                )
                if _is_challenge(response, page.title()):
                    logger.info("Skipping %s: bot-challenge page", url)
                    Path(out_path).unlink(missing_ok=True)
                    return None
                hide = [s for s in (*GENERIC_HIDE_SELECTORS, *hide_selectors) if s]
                css = f"{', '.join(hide)} {{ display: none !important; }}\n"
                css += "html, body { overflow: auto !important; }"
                page.add_style_tag(content=css)
                for sel in pre_actions:
                    try:
                        target = page.locator(sel).first
                        if target.count() > 0 and target.is_visible():
                            target.click(timeout=3000)
                            page.wait_for_timeout(300)
                    except Exception as exc:  # noqa: BLE001 - skip, never fail
                        logger.debug("Pre-action %r skipped: %s", sel, exc)
                page.wait_for_selector(
                    ", ".join([selector, *skip_selectors]), timeout=timeout_ms
                )
                if any(page.locator(s).count() > 0 for s in skip_selectors):
                    logger.info("Skipping %s: gated page", url)
                    Path(out_path).unlink(missing_ok=True)
                    return None
                _screenshot_with_retry(page, selector, out_path, timeout_ms)
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
