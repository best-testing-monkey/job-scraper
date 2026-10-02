import re

FULLY_REMOTE = "Fully Remote"
HYBRID = "Hybrid"
ON_SITE = "On-site"

_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)
_ON_SITE_RE = re.compile(r"\bon[\s-]?site\b", re.IGNORECASE)
_REMOTE_RE = re.compile(r"\b(fully[\s-]?remote|100%\s*remote|remote)\b", re.IGNORECASE)


def classify_workplace(*texts: str | None) -> str | None:
    """Mutually-exclusive workplace classification from free text (a
    location string, a badge label, etc. — any number of signals, checked
    together). Priority order matters: hybrid and on-site are checked
    before a bare "remote" mention, so "Hybrid, remote-friendly 2 days/
    week" classifies as Hybrid, not Fully Remote — hybrid and fully-remote
    must stay mutually exclusive even when both words appear. Returns None
    (unknown) when no signal is found; that is distinct from On-site,
    which requires an explicit on-site/office signal rather than being the
    default absence of a remote signal."""
    combined = " ".join(t for t in texts if t)
    if not combined:
        return None
    if _HYBRID_RE.search(combined):
        return HYBRID
    if _ON_SITE_RE.search(combined):
        return ON_SITE
    if _REMOTE_RE.search(combined):
        return FULLY_REMOTE
    return None
