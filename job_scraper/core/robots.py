from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


def robots_allowed(base_url: str, user_agent: str = "*") -> bool:
    """Fetches {scheme}://{netloc}/robots.txt for base_url, returns whether
    user_agent is allowed to fetch base_url's path per that robots.txt.
    If robots.txt itself can't be fetched (network error, 404, etc.),
    return True (fail open — absence of a robots.txt means no restriction,
    which is also the correct read for a 404)."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    rp = RobotFileParser()
    rp.set_url(robots_url)

    try:
        rp.read()
    except Exception:
        return True

    path = parsed.path or "/"
    return rp.can_fetch(user_agent, base_url)
