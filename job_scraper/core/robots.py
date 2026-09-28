from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


def robots_allowed(base_url: str, user_agent: str = "*") -> bool:
    """Fetches {scheme}://{netloc}/robots.txt for base_url, returns whether
    user_agent is allowed to fetch base_url's path per that robots.txt.
    If robots.txt itself can't be fetched for any reason (network error,
    404, timeout, or an anti-bot WAF returning 401/403 to the fetch
    itself), return True (fail open — no confirmed restriction was ever
    actually read).

    Deliberately does NOT use RobotFileParser.read() directly: that method
    swallows HTTPError itself and, for a 401/403 response specifically,
    sets disallow_all=True instead of raising — which defeats fail-open
    for exactly the WAF-interference case this function needs to handle
    (verified against a real site: a fully-open robots.txt that a WAF
    fronts with 403). Fetching manually and only handing real content to
    the parser keeps every failure mode going through the same fail-open
    path."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        request = Request(robots_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")
    except Exception:
        return True

    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.parse(content.splitlines())
    return rp.can_fetch(user_agent, base_url)
