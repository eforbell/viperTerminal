"""First-run detection for showing welcome screen."""

import json
from pathlib import Path


def get_first_run_flag_path() -> Path:
    """Get the path to the first-run flag file.

    Returns:
        Path to ~/.config/viper/first_run.json
    """
    return Path.home() / ".config" / "viper" / "first_run.json"


def is_first_run() -> bool:
    """Check if this is the first run of the application.

    Returns:
        True if this is the first run, False otherwise.
    """
    flag_path = get_first_run_flag_path()
    return not flag_path.exists()


def mark_first_run_complete() -> None:
    """Mark the first run as complete by creating the flag file."""
    flag_path = get_first_run_flag_path()
    try:
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        flag_path.write_text(json.dumps({"first_run_complete": True}))
    except OSError:
        # Fail silently - not critical if we can't persist this
        pass
