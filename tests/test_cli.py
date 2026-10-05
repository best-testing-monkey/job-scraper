import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from job_scraper.cli import main, handle_rebuild, handle_screenshots
from job_scraper.core.db import JobRepository
from job_scraper.sites.registry import SITE_REGISTRY


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    repo = JobRepository(str(db_file))
    yield repo, str(db_file)
    repo.conn.close()


def test_rebuild_help(capsys, monkeypatch):
    """Test that rebuild --help shows the expected options"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--site" in captured.out
    assert "--db" in captured.out
    assert "--jobs-dir" in captured.out
    assert "--raw-dir" in captured.out


def test_rebuild_single_site(temp_db, monkeypatch, capsys):
    """Test rebuild --site pro_act calls rebuild_site once"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--site", "pro_act", "--db", db_path])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        mock_rebuild.return_value = {"rebuilt": 5, "skipped_no_db": 1, "skipped_duplicate": 0, "excluded": 0, "errors": 0}

        main()

        # Verify rebuild_site was called once
        assert mock_rebuild.call_count == 1

        # Verify the call arguments
        call_args = mock_rebuild.call_args
        assert call_args[0][0] == "pro_act"
        assert isinstance(call_args[0][1], JobRepository)
        assert call_args[0][2] == "jobs/"
        assert call_args[0][3] == "raw/"

        # Verify output format
        captured = capsys.readouterr()
        assert "pro_act:" in captured.out
        # Parse JSON from output like "pro_act: {...}"
        line = captured.out.strip()
        json_str = line.split(": ", 1)[1]
        output_json = json.loads(json_str)
        assert output_json["rebuilt"] == 5


def test_rebuild_site_all_skips_not_rebuildable(temp_db, monkeypatch, capsys):
    """Test rebuild --site all skips NOT_REBUILDABLE sites"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--site", "all", "--db", db_path])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        mock_rebuild.return_value = {"rebuilt": 0, "skipped_no_db": 0, "skipped_duplicate": 0, "excluded": 0, "errors": 0}

        main()

        # Verify rebuild_site was called for all sites except NOT_REBUILDABLE ones
        all_sites = sorted(SITE_REGISTRY.keys())
        called_sites = [call[0][0] for call in mock_rebuild.call_args_list]

        # Check that working_nomads and tender_link are NOT in the called sites
        assert "working_nomads" not in called_sites
        assert "tender_link" not in called_sites
        assert "stone_interim" not in called_sites

        # Check that other sites ARE in the called sites
        for site in all_sites:
            if site not in ["working_nomads", "tender_link", "stone_interim"]:
                assert site in called_sites

        # Check stderr messages for skipped sites
        captured = capsys.readouterr()
        assert "Skipping working_nomads:" in captured.err
        assert "Skipping tender_link:" in captured.err
        assert "Skipping stone_interim:" in captured.err


def test_rebuild_not_rebuildable_explicit_fails(temp_db, monkeypatch, capsys):
    """Test rebuild --site working_nomads exits with code 1"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--site", "working_nomads", "--db", db_path])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

        # Verify rebuild_site was NOT called
        mock_rebuild.assert_not_called()

        # Check error message in stderr
        captured = capsys.readouterr()
        assert "Error: working_nomads cannot be rebuilt from raw:" in captured.err


def test_rebuild_without_site_fails(temp_db, monkeypatch, capsys):
    """Test rebuild without --site exits with code 1"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--db", db_path])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

        # Verify rebuild_site was NOT called
        mock_rebuild.assert_not_called()

        # Check error message in stderr
        captured = capsys.readouterr()
        assert "Error: --site is required" in captured.err


def test_rebuild_with_custom_paths(temp_db, monkeypatch, capsys):
    """Test rebuild respects custom --jobs-dir and --raw-dir"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "rebuild",
        "--site", "pro_act",
        "--db", db_path,
        "--jobs-dir", "custom_jobs/",
        "--raw-dir", "custom_raw/"
    ])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        mock_rebuild.return_value = {"rebuilt": 0, "skipped_no_db": 0, "skipped_duplicate": 0, "excluded": 0, "errors": 0}

        main()

        # Verify rebuild_site was called with custom paths
        call_args = mock_rebuild.call_args
        assert call_args[0][2] == "custom_jobs/"
        assert call_args[0][3] == "custom_raw/"


def test_rebuild_multiple_sites(temp_db, monkeypatch, capsys):
    """Test rebuild with multiple --site arguments"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "rebuild",
        "--site", "pro_act",
        "--site", "hero",
        "--db", db_path
    ])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        mock_rebuild.return_value = {"rebuilt": 0, "skipped_no_db": 0, "skipped_duplicate": 0, "excluded": 0, "errors": 0}

        main()

        # Verify rebuild_site was called for both sites
        assert mock_rebuild.call_count == 2

        called_sites = [call[0][0] for call in mock_rebuild.call_args_list]
        assert "pro_act" in called_sites
        assert "hero" in called_sites


def test_scrape_help(monkeypatch, capsys):
    """Test that scrape --help shows the screenshot options"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "scrape", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--screenshots-dir" in captured.out
    assert "--no-screenshots" in captured.out


def test_scrape_default_screenshots_dir(temp_db, monkeypatch, capsys):
    """Test scrape --site pro_act passes default screenshots_dir to run"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "scrape", "--site", "pro_act", "--db", db_path])

    with patch("job_scraper.cli.run") as mock_run:
        mock_run.return_value = {"pro_act": {"new": 1, "updated": 0, "errors": 0, "skipped": 0}}

        main()

        # Verify run was called with default screenshots_dir
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["screenshots_dir"] == "screenshots/"


def test_scrape_custom_screenshots_dir(temp_db, monkeypatch, capsys):
    """Test scrape --site pro_act --screenshots-dir /tmp/s passes custom dir to run"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "scrape",
        "--site", "pro_act",
        "--db", db_path,
        "--screenshots-dir", "/tmp/s"
    ])

    with patch("job_scraper.cli.run") as mock_run:
        mock_run.return_value = {"pro_act": {"new": 1, "updated": 0, "errors": 0, "skipped": 0}}

        main()

        # Verify run was called with custom screenshots_dir
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["screenshots_dir"] == "/tmp/s"


def test_scrape_no_screenshots(temp_db, monkeypatch, capsys):
    """Test scrape --site pro_act --no-screenshots passes None for screenshots_dir"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "scrape",
        "--site", "pro_act",
        "--db", db_path,
        "--no-screenshots"
    ])

    with patch("job_scraper.cli.run") as mock_run:
        mock_run.return_value = {"pro_act": {"new": 1, "updated": 0, "errors": 0, "skipped": 0}}

        main()

        # Verify run was called with screenshots_dir=None
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["screenshots_dir"] is None


def test_scrape_raw_dir_unchanged(temp_db, monkeypatch, capsys):
    """Test scrape respects --raw-dir and --no-raw as before"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "scrape",
        "--site", "pro_act",
        "--db", db_path,
        "--raw-dir", "custom_raw/",
        "--no-screenshots"
    ])

    with patch("job_scraper.cli.run") as mock_run:
        mock_run.return_value = {"pro_act": {"new": 1, "updated": 0, "errors": 0, "skipped": 0}}

        main()

        # Verify run was called with custom raw_dir
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["raw_dir"] == "custom_raw/"
        assert call_kwargs["screenshots_dir"] is None


def test_scrape_no_raw_still_works(temp_db, monkeypatch, capsys):
    """Test scrape --no-raw still passes raw_dir=None"""
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "scrape",
        "--site", "pro_act",
        "--db", db_path,
        "--no-raw"
    ])

    with patch("job_scraper.cli.run") as mock_run:
        mock_run.return_value = {"pro_act": {"new": 1, "updated": 0, "errors": 0, "skipped": 0}}

        main()

        # Verify run was called with raw_dir=None
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["raw_dir"] is None
        assert call_kwargs["screenshots_dir"] == "screenshots/"


def test_screenshots_help(monkeypatch, capsys):
    """Test that screenshots --help shows the expected options"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--site" in captured.out
    assert "--missing-only" in captured.out
    assert "--jobs-dir" in captured.out
    assert "--screenshots-dir" in captured.out
    assert "--prune-small" in captured.out
    assert "--min-height" in captured.out
    assert "--move-to" in captured.out
    assert "--dry-run" in captured.out


def test_screenshots_browser_not_available(monkeypatch, capsys):
    """Test screenshots exits 1 if browser_available() is False"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--site", "pro_act"])

    with patch("job_scraper.cli.browser_available", return_value=False):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_backfill.assert_not_called()

            captured = capsys.readouterr()
            assert "No Playwright Chromium found" in captured.err
            assert 'Screenshots (browser requirements)' in captured.err


def test_screenshots_single_site(monkeypatch, capsys):
    """Test screenshots --site pro_act calls backfill_screenshots once"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--site", "pro_act"])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.return_value = {
                "attempted": 5,
                "captured": 4,
                "failed": 1,
                "skipped_existing": 0,
                "skipped_no_selector": 0,
            }

            main()

            # Verify backfill_screenshots was called once with correct args
            assert mock_backfill.call_count == 1
            call_args = mock_backfill.call_args
            assert call_args[0][0] == "pro_act"
            assert call_args[0][1] == "jobs/"
            assert call_args[0][2] == "screenshots/"
            assert call_args[1]["missing_only"] is False
            assert call_args[1]["db_path"] == "scraper.db"
            assert call_args[1]["include_stale"] is False

            # Verify output format
            captured = capsys.readouterr()
            assert "pro_act:" in captured.out
            line = captured.out.strip()
            json_str = line.split(": ", 1)[1]
            output_json = json.loads(json_str)
            assert output_json["attempted"] == 5


def test_screenshots_db_and_include_stale(monkeypatch, capsys):
    """--db x.db --include-stale reach backfill_screenshots"""
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "screenshots", "--site", "pro_act",
        "--db", "x.db", "--include-stale",
    ])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.return_value = {"attempted": 0}
            main()

            kwargs = mock_backfill.call_args[1]
            assert kwargs["db_path"] == "x.db"
            assert kwargs["include_stale"] is True


def test_screenshots_missing_only(monkeypatch, capsys):
    """Test screenshots --missing-only passes the flag to backfill_screenshots"""
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "screenshots",
        "--site", "pro_act",
        "--missing-only"
    ])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.return_value = {
                "attempted": 2,
                "captured": 2,
                "failed": 0,
                "skipped_existing": 3,
                "skipped_no_selector": 0,
            }

            main()

            # Verify missing_only=True was passed
            call_args = mock_backfill.call_args
            assert call_args[1]["missing_only"] is True


def test_screenshots_custom_paths(monkeypatch, capsys):
    """Test screenshots with custom --jobs-dir and --screenshots-dir"""
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "screenshots",
        "--site", "pro_act",
        "--jobs-dir", "custom_jobs/",
        "--screenshots-dir", "custom_screenshots/"
    ])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.return_value = {
                "attempted": 0,
                "captured": 0,
                "failed": 0,
                "skipped_existing": 0,
                "skipped_no_selector": 5,
            }

            main()

            # Verify custom paths were passed
            call_args = mock_backfill.call_args
            assert call_args[0][1] == "custom_jobs/"
            assert call_args[0][2] == "custom_screenshots/"


def test_screenshots_site_all(monkeypatch, capsys):
    """Test screenshots --site all runs for all sites"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--site", "all"])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.return_value = {
                "attempted": 0,
                "captured": 0,
                "failed": 0,
                "skipped_existing": 0,
                "skipped_no_selector": 0,
            }

            main()

            # Verify backfill_screenshots was called for all sites
            all_sites = sorted(SITE_REGISTRY.keys())
            called_sites = [call[0][0] for call in mock_backfill.call_args_list]
            assert len(called_sites) == len(all_sites)
            assert set(called_sites) == set(all_sites)
            # Verify they were called in sorted order
            assert called_sites == all_sites


def test_screenshots_without_site_fails(monkeypatch, capsys):
    """Test screenshots without --site exits with code 1"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots"])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_backfill.assert_not_called()

            captured = capsys.readouterr()
            assert "Error: --site is required" in captured.err


def test_screenshots_unknown_site_fails(monkeypatch, capsys):
    """Test screenshots with unknown site ID exits with code 1"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--site", "nonexistent_site"])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.side_effect = ValueError("Unknown site_id: nonexistent_site")

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            assert "Error: Unknown site_id: nonexistent_site" in captured.err


def test_screenshots_multiple_sites(monkeypatch, capsys):
    """Test screenshots with multiple --site arguments"""
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "screenshots",
        "--site", "pro_act",
        "--site", "hero"
    ])

    with patch("job_scraper.cli.browser_available", return_value=True):
        with patch("job_scraper.cli.backfill_screenshots") as mock_backfill:
            mock_backfill.return_value = {
                "attempted": 0,
                "captured": 0,
                "failed": 0,
                "skipped_existing": 0,
                "skipped_no_selector": 0,
            }

            main()

            # Verify backfill_screenshots was called for both sites
            assert mock_backfill.call_count == 2

            called_sites = [call[0][0] for call in mock_backfill.call_args_list]
            assert "pro_act" in called_sites
            assert "hero" in called_sites


def test_stale_sync_prints_counters(temp_db, tmp_path, monkeypatch, capsys):
    """stale-sync prints one JSON line with the five counter keys"""
    repo, db_path = temp_db
    jobs_dir = str(tmp_path / "jobs")
    monkeypatch.setattr(sys, "argv", ["job_scraper", "stale-sync", "--db", db_path, "--jobs-dir", jobs_dir])

    main()

    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    assert set(json.loads(out[0])) == {"stale_rows", "dated", "written", "cleared", "missing_md"}


def test_stale_sync_help(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["job_scraper", "stale-sync", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--db" in out
    assert "--jobs-dir" in out


def test_scrape_prints_counters_incrementally_once(temp_db, monkeypatch, capsys):
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "scrape", "--site", "a", "--site", "b", "--db", db_path])

    def fake_run(site_ids, repo, jobs_dir, **kwargs):
        results = {"a": {"seen": 1}, "b": {"seen": 2}}
        for sid, c in results.items():
            kwargs["on_site_done"](sid, c)
        return results

    with patch("job_scraper.cli.run", side_effect=fake_run):
        main()

    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith(("a:", "b:"))]
    assert lines == ['a: {"seen": 1}', 'b: {"seen": 2}']


def test_scrape_exits_1_on_site_error(temp_db, monkeypatch, capsys):
    repo, db_path = temp_db
    monkeypatch.setattr(sys, "argv", ["job_scraper", "scrape", "--site", "a", "--db", db_path])

    with patch("job_scraper.cli.run", return_value={"a": {"seen": 1, "error": "RuntimeError: boom"}}):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    assert 'a: {"seen": 1, "error": "RuntimeError: boom"}' in capsys.readouterr().out


def test_screenshots_prune_small_dry_run_no_site(monkeypatch, capsys):
    """Test screenshots --prune-small --dry-run with no site"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--prune-small", "--dry-run"])

    with patch("job_scraper.cli.prune_small_screenshots") as mock_prune:
        with patch("job_scraper.cli.browser_available") as mock_browser:
            mock_prune.return_value = {
                "scanned": 10,
                "small": 3,
                "moved": 0,
                "markdown_updated": 0,
                "unreadable": 0,
                "skipped_exists": 0,
            }

            main()

            # Verify browser_available was not called
            mock_browser.assert_not_called()

            # Verify prune_small_screenshots was called with sites=None
            mock_prune.assert_called_once()
            call_kwargs = mock_prune.call_args[1]
            assert call_kwargs["sites"] is None
            assert call_kwargs["dry_run"] is True
            assert call_kwargs["move_to"] is None

            # Verify output is one JSON line
            captured = capsys.readouterr()
            lines = captured.out.strip().splitlines()
            assert len(lines) == 1
            output_json = json.loads(lines[0])
            assert output_json["scanned"] == 10


def test_screenshots_prune_small_with_sites_and_move_to(monkeypatch, capsys):
    """Test screenshots --prune-small --site hero --site harveynash --move-to /x --min-height 120"""
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "screenshots", "--prune-small",
        "--site", "hero",
        "--site", "harveynash",
        "--move-to", "/x",
        "--min-height", "120"
    ])

    with patch("job_scraper.cli.prune_small_screenshots") as mock_prune:
        with patch("job_scraper.cli.browser_available") as mock_browser:
            mock_prune.return_value = {
                "scanned": 5,
                "small": 2,
                "moved": 2,
                "markdown_updated": 2,
                "unreadable": 0,
                "skipped_exists": 0,
            }

            main()

            # Verify browser_available was not called
            mock_browser.assert_not_called()

            # Verify prune_small_screenshots was called with correct arguments
            mock_prune.assert_called_once()
            call_kwargs = mock_prune.call_args[1]
            assert call_kwargs["sites"] == ["hero", "harveynash"]
            assert call_kwargs["min_height"] == 120
            assert call_kwargs["move_to"] == "/x"
            assert call_kwargs["dry_run"] is False

            # Verify positional arguments
            call_args = mock_prune.call_args[0]
            assert call_args[0] == "screenshots/"
            assert call_args[1] == "jobs/"


def test_screenshots_prune_small_no_move_to_no_dry_run_fails(monkeypatch, capsys):
    """Test screenshots --prune-small without --move-to and without --dry-run exits 1"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "screenshots", "--prune-small"])

    with patch("job_scraper.cli.prune_small_screenshots") as mock_prune:
        with patch("job_scraper.cli.browser_available") as mock_browser:
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            # Verify prune_small_screenshots was NOT called
            mock_prune.assert_not_called()

            # Verify browser_available was not called
            mock_browser.assert_not_called()

            # Verify error message on stderr
            captured = capsys.readouterr()
            assert "Error: --move-to is required unless --dry-run" in captured.err


def test_screenshots_prune_small_all_sites(monkeypatch, capsys):
    """Test screenshots --prune-small --site all expands to all sites"""
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "screenshots", "--prune-small",
        "--site", "all",
        "--move-to", "/tmp/prune",
        "--dry-run"
    ])

    with patch("job_scraper.cli.prune_small_screenshots") as mock_prune:
        with patch("job_scraper.cli.browser_available") as mock_browser:
            mock_prune.return_value = {
                "scanned": 100,
                "small": 0,
                "moved": 0,
                "markdown_updated": 0,
                "unreadable": 0,
                "skipped_exists": 0,
            }

            main()

            # Verify browser_available was not called
            mock_browser.assert_not_called()

            # Verify prune_small_screenshots was called with all sites
            mock_prune.assert_called_once()
            call_kwargs = mock_prune.call_args[1]
            all_sites = sorted(SITE_REGISTRY.keys())
            assert call_kwargs["sites"] == all_sites
