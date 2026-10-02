from unittest.mock import patch

import pytest

from job_scraper.core import screenshot_backfill as sb
from job_scraper.sites.base import FetchStrategy
from job_scraper.sites.registry import SITE_REGISTRY

MD = "# T\n\n- Source: https://x.test/{n}\n- Client: C\n\n## Description\n\nBody\n"


class FakeAdapter:
    site_id = "fake"
    screenshot_selector = "div.x"
    fetch_strategy = FetchStrategy.STATIC


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setitem(SITE_REGISTRY, "fake", FakeAdapter)
    monkeypatch.setattr(FakeAdapter, "screenshot_selector", "div.x")
    jobs = tmp_path / "jobs"
    shots = tmp_path / "shots"
    jobs.mkdir()
    shots.mkdir()
    for n in ("a", "b"):
        (jobs / f"fake-{n}-t.md").write_text(MD.format(n=n))
    (jobs / "other-1-t.md").write_text(MD.format(n="o"))
    return jobs, shots


def run(env, **kw):
    jobs, shots = env
    return sb.backfill_screenshots("fake", str(jobs), str(shots), delay=0, **kw)


def test_unknown_site(env):
    with pytest.raises(ValueError):
        sb.backfill_screenshots("nope", "j", "s")


def test_all_success(env):
    with patch.object(sb, "capture_element", return_value=True) as cap:
        res = run(env)
    assert res == {
        "attempted": 2,
        "captured": 2,
        "failed": 0,
        "skipped_existing": 0,
        "skipped_no_selector": 0,
    }
    assert cap.call_args_list[0].args[:2] == ("https://x.test/a", "div.x")
    assert cap.call_args_list[0].kwargs == {"stealth": False}
    text = (env[0] / "fake-a-t.md").read_text()
    assert "- Screenshot: screenshots/fake-a-t.png" in text
    assert "Screenshot" not in (env[0] / "other-1-t.md").read_text()


def test_failures_and_exception(env):
    with patch.object(sb, "capture_element", side_effect=[RuntimeError("boom"), False]):
        res = run(env)
    assert res["attempted"] == 2 and res["failed"] == 2 and res["captured"] == 0
    assert "Screenshot" not in (env[0] / "fake-a-t.md").read_text()


def test_missing_only(env):
    jobs, shots = env
    (shots / "fake-a-t.png").write_bytes(b"png")
    with patch.object(sb, "capture_element", return_value=True) as cap:
        res = run(env, missing_only=True)
    assert res["skipped_existing"] == 1 and res["captured"] == 1
    assert cap.call_count == 1
    assert "- Screenshot: screenshots/fake-a-t.png" in (jobs / "fake-a-t.md").read_text()


def test_no_source_line(env):
    jobs, _ = env
    (jobs / "fake-c-t.md").write_text("# T\n\n- Client: C\n\n## Description\n\nB\n")
    with patch.object(sb, "capture_element", return_value=True):
        res = run(env)
    assert res["failed"] == 1 and res["captured"] == 2


def test_no_selector(env, monkeypatch):
    monkeypatch.setattr(FakeAdapter, "screenshot_selector", None)
    with patch.object(sb, "capture_element") as cap:
        res = run(env)
    assert res["skipped_no_selector"] == 2 and res["attempted"] == 0
    cap.assert_not_called()


def test_stealth_flag(env, monkeypatch):
    monkeypatch.setattr(FakeAdapter, "fetch_strategy", FetchStrategy.STEALTH)
    with patch.object(sb, "capture_element", return_value=True) as cap:
        run(env)
    assert cap.call_args.kwargs == {"stealth": True}


def test_idempotent_single_line(env):
    with patch.object(sb, "capture_element", return_value=True):
        run(env)
        run(env)
    for n in ("a", "b"):
        text = (env[0] / f"fake-{n}-t.md").read_text()
        assert text.count("- Screenshot:") == 1
