from collections import deque
from copy import deepcopy
from datetime import UTC, datetime
from itertools import count
from threading import Lock
from typing import Any

MAX_HISTORY_ENTRIES = 100

_entries: deque[dict[str, Any]] = deque(maxlen=MAX_HISTORY_ENTRIES)
_entry_ids = count(1)
_lock = Lock()


def record_exchange(
    request: dict[str, Any],
    response: dict[str, Any],
    status_code: int,
) -> None:
    """Record one decision request and its HTTP response."""
    request_snapshot = deepcopy(request)
    response_snapshot = deepcopy(response)
    with _lock:
        _entries.append(
            {
                "id": next(_entry_ids),
                "timestamp": datetime.now(UTC).isoformat(),
                "status_code": status_code,
                "request": request_snapshot,
                "response": response_snapshot,
            }
        )


def get_history() -> list[dict[str, Any]]:
    """Return a snapshot of recorded exchanges, newest first."""
    with _lock:
        return deepcopy(list(reversed(_entries)))
