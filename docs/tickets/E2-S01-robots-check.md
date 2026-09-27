# E2-S01: robots.txt pre-check

Read `docs/tickets/APPENDIX-A-standards.md` first. Depends only on `E0-S01`
(no dependency on models/db).

## Goal

A single function that tells the pipeline whether a site's base URL may be
crawled by a generic user-agent, per that domain's `robots.txt`.

## Context

Create: `job_scraper/core/robots.py`, `tests/test_robots.py`.

Use stdlib `urllib.robotparser.RobotFileParser` only — no new dependency.

```python
def robots_allowed(base_url: str, user_agent: str = "*") -> bool:
    """Fetches {scheme}://{netloc}/robots.txt for base_url, returns whether
    user_agent is allowed to fetch base_url's path per that robots.txt.
    If robots.txt itself can't be fetched (network error, 404, etc.),
    return True (fail open — absence of a robots.txt means no restriction,
    which is also the correct read for a 404)."""
```

## Acceptance criteria

- `tests/test_robots.py` does NOT make live network calls. Instead,
  monkeypatch/stub `RobotFileParser.read` (or construct a
  `RobotFileParser`, call `.parse()` with literal robots.txt line lists, and
  test the underlying `.can_fetch()` logic your function wraps) to simulate:
  - a robots.txt that disallows `/` for `*` → `robots_allowed` returns
    `False`.
  - a robots.txt that allows everything → returns `True`.
  - `read()` raising an exception (simulating a fetch failure) → returns
    `True` (fail open).
- Exact test mechanics (mocking `urlopen`, subclassing `RobotFileParser`, or
  using `unittest.mock.patch`) are your choice — the three behaviors above
  must be independently verifiable and must not touch the network.

## Definition of done

Per Appendix A.
