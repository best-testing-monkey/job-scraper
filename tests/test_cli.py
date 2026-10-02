import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from job_scraper.cli import main, handle_rebuild
from job_scraper.core.db import JobRepository
from job_scraper.sites.registry import SITE_REGISTRY


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test.db"
    repo = JobRepository(str(db_file))
    yield repo
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
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--site", "pro_act", "--db", str(temp_db.conn)])

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
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--site", "all", "--db", str(temp_db.conn)])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        mock_rebuild.return_value = {"rebuilt": 0, "skipped_no_db": 0, "skipped_duplicate": 0, "excluded": 0, "errors": 0}

        main()

        # Verify rebuild_site was called for all sites except NOT_REBUILDABLE ones
        all_sites = sorted(SITE_REGISTRY.keys())
        called_sites = [call[0][0] for call in mock_rebuild.call_args_list]

        # Check that working_nomads and tender_link are NOT in the called sites
        assert "working_nomads" not in called_sites
        assert "tender_link" not in called_sites

        # Check that other sites ARE in the called sites
        for site in all_sites:
            if site not in ["working_nomads", "tender_link"]:
                assert site in called_sites

        # Check stderr messages for skipped sites
        captured = capsys.readouterr()
        assert "Skipping working_nomads:" in captured.err
        assert "Skipping tender_link:" in captured.err


def test_rebuild_not_rebuildable_explicit_fails(temp_db, monkeypatch, capsys):
    """Test rebuild --site working_nomads exits with code 1"""
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--site", "working_nomads", "--db", str(temp_db.conn)])

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
    monkeypatch.setattr(sys, "argv", ["job_scraper", "rebuild", "--db", str(temp_db.conn)])

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
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "rebuild",
        "--site", "pro_act",
        "--db", str(temp_db.conn),
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
    monkeypatch.setattr(sys, "argv", [
        "job_scraper", "rebuild",
        "--site", "pro_act",
        "--site", "hero",
        "--db", str(temp_db.conn)
    ])

    with patch("job_scraper.cli.rebuild_site") as mock_rebuild:
        mock_rebuild.return_value = {"rebuilt": 0, "skipped_no_db": 0, "skipped_duplicate": 0, "excluded": 0, "errors": 0}

        main()

        # Verify rebuild_site was called for both sites
        assert mock_rebuild.call_count == 2

        called_sites = [call[0][0] for call in mock_rebuild.call_args_list]
        assert "pro_act" in called_sites
        assert "hero" in called_sites
