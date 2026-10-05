import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

_MAX_CHARS = 300000
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class GoneCheck:
    listing_id: str = ""
    listing_paths: tuple[str, ...] = ()
    gone_markers: tuple[str, ...] = ()


def _normalise(url: str) -> tuple[str, str]:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = unquote(parts.path).rstrip("/")
    return host, path or "/"


def _segments(path: str) -> list[str]:
    return [s for s in path.split("/") if s]


def is_unrelated_redirect(
    requested_url: str,
    final_url: str,
    listing_id: str = "",
    listing_paths: Sequence[str] = (),
) -> bool:
    req_host, req_path = _normalise(requested_url)
    fin_host, fin_path = _normalise(final_url)
    if (req_host, req_path) == (fin_host, fin_path):
        return False
    if req_host != fin_host:
        return False
    if listing_id and listing_id.lower() in fin_path.lower():
        return False
    if fin_path == "/":
        return True
    for lp in listing_paths:
        lp = lp.rstrip("/") or "/"
        if fin_path == lp or fin_path.endswith(lp if lp.startswith("/") else "/" + lp):
            return True
    if not listing_paths and listing_id:
        return len(_segments(fin_path)) < len(_segments(req_path))
    return False


def _as_text(body: bytes | str) -> str:
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="ignore")
    return body[:_MAX_CHARS]


def _clean(fragment: str) -> str:
    return _SPACE_RE.sub(" ", _TAG_RE.sub("", fragment)).strip()


def title_has_gone_marker(body: bytes | str, markers: Sequence[str]) -> str | None:
    if not markers:
        return None
    text = _as_text(body)
    fragments = [_clean(m) for m in _TITLE_RE.findall(text)]
    fragments += [_clean(m) for m in _H1_RE.findall(text)]
    lowered = [f.lower() for f in fragments]
    for marker in markers:
        if marker and any(marker.lower() in f for f in lowered):
            return marker
    return None


def gone_reason(
    status: int | None,
    requested_url: str,
    final_url: str | None,
    body: bytes | str | None,
    check: GoneCheck,
) -> str | None:
    if status in (404, 410):
        return f"http {status}"
    if final_url and is_unrelated_redirect(
        requested_url, final_url, check.listing_id, check.listing_paths
    ):
        return f"redirect to {_normalise(final_url)[1]}"
    if body is not None:
        marker = title_has_gone_marker(body, check.gone_markers)
        if marker:
            return f"marker '{marker}'"
    return None
