from unittest.mock import patch

import pytest

from job_scraper.core import screenshot_backfill as sb
from job_scraper.core.db import JobRepository
from job_scraper.core.models import JobPosting
from job_scraper.sites.base import FetchStrategy
from job_scraper.sites.registry import SITE_REGISTRY

MD = "# T\n\n- Source: https://x.test/{n}\n- Client: C\n\n## Description\n\nBody\n"


class FakeAdapter:
    site_id = "fake"
    screenshot_selector = "div.x"
    screenshot_hide_selectors = ()
    screenshot_pre_actions = ()
    screenshot_skip_selectors = ()
    screenshot_min_height = 100
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
        "skipped_blocked": 0,
        "skipped_stale": 0,
    }
    assert cap.call_args_list[0].args[:2] == ("https://x.test/a", "div.x")
    assert cap.call_args_list[0].kwargs == {"stealth": False, "hide_selectors": (), "pre_actions": (), "skip_selectors": (), "min_height": 100}
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


def test_hide_selectors_passed(env, monkeypatch):
    monkeypatch.setattr(FakeAdapter, "screenshot_hide_selectors", ("div.form", "#banner"))
    with patch.object(sb, "capture_element", return_value=True) as cap:
        run(env)
    assert cap.call_args.kwargs["hide_selectors"] == FakeAdapter.screenshot_hide_selectors


def test_stealth_flag(env, monkeypatch):
    monkeypatch.setattr(FakeAdapter, "fetch_strategy", FetchStrategy.STEALTH)
    with patch.object(sb, "capture_element", return_value=True) as cap:
        run(env)
    assert cap.call_args.kwargs == {"stealth": True, "hide_selectors": (), "pre_actions": (), "skip_selectors": (), "min_height": 100}


def test_idempotent_single_line(env):
    with patch.object(sb, "capture_element", return_value=True):
        run(env)
        run(env)
    for n in ("a", "b"):
        text = (env[0] / f"fake-{n}-t.md").read_text()
        assert text.count("- Screenshot:") == 1


def test_none_counts_skipped_blocked(env):
    jobs, _ = env
    before_a = (jobs / "fake-a-t.md").read_bytes()
    before_b = (jobs / "fake-b-t.md").read_bytes()
    with patch.object(sb, "capture_element", return_value=None):
        res = run(env)
    assert res["skipped_blocked"] == 2
    assert res["failed"] == 0
    assert res["captured"] == 0
    assert res["attempted"] == 2
    assert (jobs / "fake-a-t.md").read_bytes() == before_a
    assert (jobs / "fake-b-t.md").read_bytes() == before_b


def test_pre_actions_and_skip_selectors_passed(env, monkeypatch):
    class PreActionSkipAdapter(FakeAdapter):
        screenshot_pre_actions = ("click:button.load", "wait:div.content")
        screenshot_skip_selectors = ("div.no-ad", "span.skip")

    monkeypatch.setitem(SITE_REGISTRY, "fake", PreActionSkipAdapter)
    with patch.object(sb, "capture_element", return_value=True) as cap:
        run(env)
    assert cap.call_args_list[0].kwargs["pre_actions"] == ("click:button.load", "wait:div.content")
    assert cap.call_args_list[0].kwargs["skip_selectors"] == ("div.no-ad", "span.skip")


def _stale_db(tmp_path):
    db = tmp_path / "s.db"
    repo = JobRepository(str(db))
    for lid in ("a", "b"):
        posting = JobPosting(site_id="fake", listing_id=lid, source_url=f"https://x.test/{lid}", title="t")
        repo.upsert(posting, "2026-01-01T00:00:00Z" if lid == "a" else "2026-02-01T00:00:00Z")
    assert repo.mark_stale_not_seen_since("fake", "2026-02-01T00:00:00Z") == 1
    repo.conn.close()
    return str(db)


def test_stale_skipped(env, tmp_path):
    jobs, _ = env
    db = _stale_db(tmp_path)
    before = (jobs / "fake-a-t.md").read_bytes()
    with patch.object(sb, "capture_element", return_value=True) as cap:
        res = run(env, db_path=db)
    assert cap.call_count == 1
    assert cap.call_args.args[0] == "https://x.test/b"
    assert res["skipped_stale"] == 1
    assert res["captured"] == 1
    assert (jobs / "fake-a-t.md").read_bytes() == before


def test_include_stale_captures_all(env, tmp_path):
    db = _stale_db(tmp_path)
    with patch.object(sb, "capture_element", return_value=True) as cap:
        res = run(env, db_path=db, include_stale=True)
    assert cap.call_count == 2
    assert res["skipped_stale"] == 0


def test_missing_db_skips_nothing(env, tmp_path):
    with patch.object(sb, "capture_element", return_value=True) as cap:
        res = run(env, db_path=str(tmp_path / "nope.db"))
    assert cap.call_count == 2
    assert res["skipped_stale"] == 0


def test_min_height_passed(env, monkeypatch):
    monkeypatch.setattr(FakeAdapter, "screenshot_min_height", 150)
    with patch.object(sb, "capture_element", return_value=True) as cap:
        run(env)
    assert cap.call_args.kwargs["min_height"] == 150


def test_site_registry_has_min_height():
    for site_id, adapter_cls in SITE_REGISTRY.items():
        assert hasattr(adapter_cls, "screenshot_min_height")
        min_height = adapter_cls.screenshot_min_height
        assert isinstance(min_height, int), f"{site_id}.screenshot_min_height is {type(min_height)}, not int"
        assert min_height > 0, f"{site_id}.screenshot_min_height is {min_height}, not > 0"
