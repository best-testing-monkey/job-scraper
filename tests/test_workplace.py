from job_scraper.core.workplace import classify_workplace


def test_fully_remote_from_badge() -> None:
    assert classify_workplace("Barcelona, Spain", "Remote") == "Fully Remote"


def test_fully_remote_from_location_text() -> None:
    assert classify_workplace("Fully Remote(UTC+2 timezone)", None) == "Fully Remote"


def test_hybrid_wins_over_remote_mention() -> None:
    assert classify_workplace("Hybrid, remote-friendly 2 days/week", None) == "Hybrid"


def test_hybrid_wins_over_remote_badge() -> None:
    assert classify_workplace("Hybrid - Amsterdam", "Remote") == "Hybrid"


def test_on_site() -> None:
    assert classify_workplace("On-site, Berlin", None) == "On-site"
    assert classify_workplace("Onsite in NYC office", None) == "On-site"


def test_on_site_wins_over_remote_mention() -> None:
    assert classify_workplace("On-site with occasional remote days", None) == "On-site"


def test_unknown_when_no_signal() -> None:
    assert classify_workplace("Pontevedra, Spain", None) is None


def test_unknown_when_all_none() -> None:
    assert classify_workplace(None, None) is None


def test_mutually_exclusive_never_both() -> None:
    for text in [
        "Hybrid remote on-site flexible",
        "Remote or hybrid or on-site, your choice",
    ]:
        result = classify_workplace(text, None)
        assert result in ("Hybrid", "On-site", "Fully Remote")
