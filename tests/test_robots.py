from unittest.mock import MagicMock, patch

from job_scraper.core.robots import robots_allowed


def _fake_urlopen(body: bytes) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = False
    return cm


def test_robots_disallow_root_returns_false() -> None:
    """A robots.txt body disallowing / for * returns False."""
    body = b"User-agent: *\nDisallow: /\n"
    with patch("job_scraper.core.robots.urlopen", return_value=_fake_urlopen(body)):
        result = robots_allowed("https://example.com/path", user_agent="*")
    assert result is False


def test_robots_allow_all_returns_true() -> None:
    """A robots.txt body allowing everything returns True."""
    body = b"User-agent: *\nDisallow:\n"
    with patch("job_scraper.core.robots.urlopen", return_value=_fake_urlopen(body)):
        result = robots_allowed("https://example.com/path", user_agent="*")
    assert result is True


def test_robots_read_exception_returns_true() -> None:
    """A fetch exception (network error, timeout, etc.) fails open -> True."""
    with patch("job_scraper.core.robots.urlopen", side_effect=Exception("Network error")):
        result = robots_allowed("https://example.com/path", user_agent="*")
    assert result is True


def test_robots_403_from_waf_fails_open_returns_true() -> None:
    """An HTTP 403 raised while fetching robots.txt (e.g. an anti-bot WAF,
    not a real robots.txt Disallow) must also fail open -> True, not be
    silently absorbed into RobotFileParser's own disallow-on-403 behavior."""
    from urllib.error import HTTPError

    err = HTTPError("https://example.com/robots.txt", 403, "Forbidden", {}, None)
    with patch("job_scraper.core.robots.urlopen", side_effect=err):
        result = robots_allowed("https://example.com/path", user_agent="*")
    assert result is True
