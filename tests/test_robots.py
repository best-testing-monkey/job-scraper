from unittest.mock import MagicMock, patch

from job_scraper.core.robots import robots_allowed


def test_robots_disallow_root_returns_false() -> None:
    """Test that a robots.txt disallowing / for * returns False."""
    with patch("job_scraper.core.robots.RobotFileParser") as mock_rp_class:
        mock_instance = MagicMock()
        mock_rp_class.return_value = mock_instance
        mock_instance.can_fetch.return_value = False

        result = robots_allowed("https://example.com/path", user_agent="*")

        assert result is False
        mock_instance.set_url.assert_called_once_with(
            "https://example.com/robots.txt"
        )
        mock_instance.read.assert_called_once()
        mock_instance.can_fetch.assert_called_once_with(
            "*", "https://example.com/path"
        )


def test_robots_allow_all_returns_true() -> None:
    """Test that a robots.txt allowing everything returns True."""
    with patch("job_scraper.core.robots.RobotFileParser") as mock_rp_class:
        mock_instance = MagicMock()
        mock_rp_class.return_value = mock_instance
        mock_instance.can_fetch.return_value = True

        result = robots_allowed("https://example.com/path", user_agent="*")

        assert result is True
        mock_instance.set_url.assert_called_once_with(
            "https://example.com/robots.txt"
        )
        mock_instance.read.assert_called_once()
        mock_instance.can_fetch.assert_called_once_with(
            "*", "https://example.com/path"
        )


def test_robots_read_exception_returns_true() -> None:
    """Test that a read() exception (e.g., 404, network error) returns True."""
    with patch("job_scraper.core.robots.RobotFileParser") as mock_rp_class:
        mock_instance = MagicMock()
        mock_rp_class.return_value = mock_instance
        mock_instance.read.side_effect = Exception("Network error")

        result = robots_allowed("https://example.com/path", user_agent="*")

        assert result is True
        mock_instance.set_url.assert_called_once_with(
            "https://example.com/robots.txt"
        )
        mock_instance.read.assert_called_once()
