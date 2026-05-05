"""Utility functions for the CAD Generator backend."""
from datetime import datetime, timezone


def now() -> datetime:
    """Get current UTC datetime. Replaces deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)
