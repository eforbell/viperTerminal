"""Serialization helpers for MCP tool responses."""

from datetime import datetime


def serialize_datetime(dt: datetime) -> str:
    """Convert a datetime to ISO 8601 string.

    Args:
        dt: Datetime object to serialize

    Returns:
        ISO 8601 formatted string
    """
    return dt.isoformat()
