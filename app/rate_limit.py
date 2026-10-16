import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from .config import settings

_buckets = defaultdict(deque)
_lock = threading.Lock()


def reset_rate_limits() -> None:
    """Borra los contadores (se usa en los tests)."""
    with _lock:
        _buckets.clear()


def rate_limit(name: str, max_calls: int, window_seconds: int):
    """Dependencia que permite `max_calls` peticiones por IP cada `window_seconds`."""

    def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        ip = request.client.host if request.client else "desconocida"
        key = (name, ip)
        now = time.monotonic()
        with _lock:
            calls = _buckets[key]
            while calls and now - calls[0] > window_seconds:
                calls.popleft()  # descarta peticiones fuera de la ventana
            if len(calls) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiadas solicitudes. Intenta de nuevo más tarde.",
                )
            calls.append(now)

    return dependency