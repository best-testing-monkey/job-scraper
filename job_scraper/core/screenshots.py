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


def _title_is_challenge(title: str) -> bool:
    t = title.lower()
    return "just a moment" in t or "attention required" in t


def _is_challenge(response, title: str) -> bool:
    """True iff the response is a bot-wall challenge page (detect and skip only)."""
    if response is None:
        return False
    if response.headers.get("cf-mitigated") == "challenge":
        return True
    return response.status in (403, 503) and _title_is_challenge(title)


SETTLE_JS = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) return true;
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    if (parseFloat(getComputedStyle(n).opacity) < 0.99) return false;
  }
  for (const a of document.getAnimations()) {
    if (a.playState !== 'running') continue;
    const t = a.effect && a.effect.target;
    if (!t || !t.contains(el)) continue;
    let iters = 1;
    try { iters = a.effect.getComputedTiming().iterations; } catch (e) {}
    if (iters !== Infinity) return false;
  }
  return true;
}
"""


def _settle(page, selector, max_ms=3000) -> None:
    """Scroll the target into view, then wait for fade-ins to finish. Never raises.

    AOS-style fades only start once the element scrolls into view, so the
    scroll comes first; the wait is bounded by ``max_ms``.
    """
    try:
        page.locator(selector).first.scroll_into_view_if_needed(timeout=3000)
    except Exception as exc:  # noqa: BLE001 - settle never fails a capture
        logger.debug("Settle scroll skipped: %s", exc)
    try:
        page.wait_for_function(SETTLE_JS, arg=selector, timeout=max_ms)
    except Exception as exc:  # noqa: BLE001 - timeout: capture anyway
        logger.debug("Settle wait ended: %s", exc)
    try:
        page.wait_for_timeout(100)
    except Exception:  # noqa: BLE001
        pass


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


def _capture_on_page(
    page, response, url, selector, out_path, timeout_ms,
    hide_selectors, pre_actions, skip_selectors,
) -> bool | None:
    """Per-page work shared by the plain-Playwright and StealthyFetcher paths.

    Returns True saved, None skipped (challenge / gated page; no file left).
    Raises on failure (callers turn that into False). ``response`` may be None
    (stealth path: the status is checked by the caller after the fetch).
    """
    title = page.title()
    if _is_challenge(response, title) or (
        response is None and _title_is_challenge(title)
    ):
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
    _settle(page, selector)
    _screenshot_with_retry(page, selector, out_path, timeout_ms)
    return True


def _capture_stealth(
    url, selector, out_path, timeout_ms, hide_selectors, pre_actions, skip_selectors
) -> bool | None:
    """Capture inside scrapling's StealthyFetcher browser (patchright Chromium).

    Differences from the plain path (fetcher limits): the fetcher owns launch
    and navigation (``page.goto`` plus its load/stability waits; its
    ``timeout`` is in ms like ours) and uses a 1920x1080 viewport, so the page
    is resized to the plain-path viewport inside ``page_action``. The Response
    status/headers exist only after ``fetch`` returns, so inside the callback
    only the title is checked; status/headers are checked afterwards.
    scrapling swallows ``page_action`` exceptions, hence the closure.
    No challenge-solving option is ever passed.
    """
    from scrapling.fetchers import StealthyFetcher

    outcome: dict = {"result": False, "error": None}

    def page_action(page):
        try:
            page.set_viewport_size(_VIEWPORT)
            outcome["result"] = _capture_on_page(
                page, None, url, selector, out_path, timeout_ms,
                hide_selectors, pre_actions, skip_selectors,
            )
        except Exception as exc:  # noqa: BLE001 - recorded, reported as False
            outcome["error"] = exc
            outcome["result"] = False
        return page

    response = StealthyFetcher.fetch(
        url, headless=True, timeout=timeout_ms, page_action=page_action
    )
    if outcome["error"] is not None:
        raise outcome["error"]
    try:
        title = str(response.css("title::text").get() or "")
    except Exception:  # noqa: BLE001
        title = ""
    if outcome["result"] is None or _is_challenge(response, title):
        logger.info("Skipping %s: bot-challenge page", url)
        Path(out_path).unlink(missing_ok=True)
        return None
    return bool(outcome["result"])


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
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        if stealth:
            return _capture_stealth(
                url, selector, out_path, timeout_ms,
                hide_selectors, pre_actions, skip_selectors,
            )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=_VIEWPORT)
                response = page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout_ms
                )
                result = _capture_on_page(
                    page, response, url, selector, out_path, timeout_ms,
                    hide_selectors, pre_actions, skip_selectors,
                )
            finally:
                browser.close()
        return result
    except Exception as exc:  # noqa: BLE001 - contract: never raise
        logger.warning("Screenshot of %s failed: %s", url, exc)
        try:
            Path(out_path).unlink(missing_ok=True)
        except OSError:
            pass
        return False
