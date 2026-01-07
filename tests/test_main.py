"""Tests for the main entry point."""

from unittest.mock import MagicMock, patch

from viper.__main__ import main


def test_main_creates_and_runs_app() -> None:
    """Test that main() creates a ViperApp and runs it."""
    with patch("viper.__main__.ViperApp") as mock_app_class:
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance

        main()

        mock_app_class.assert_called_once()
        mock_app_instance.run.assert_called_once()
