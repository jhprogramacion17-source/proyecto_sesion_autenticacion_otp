from datetime import datetime, timezone


def utcnow() -> datetime:
    """Fecha y hora actual en UTC, sin zona horaria (naive)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)