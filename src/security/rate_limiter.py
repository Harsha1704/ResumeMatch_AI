"""
src/security/rate_limiter.py
In-memory sliding-window rate limiter:
- Protects API and web upload endpoints from brute-force and resource exhaustion.
- Thread-safe using threading.Lock.
- Automatic cleanup of expired timestamps.
- Returns retry-after duration for HTTP 429 Too Many Requests responses.
"""

import time
import threading
from typing import Dict, List, Tuple


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> Tuple[bool, float]:
        """
        Checks whether client_id is within rate limits.
        Returns:
            (allowed: bool, retry_after_seconds: float)
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Get existing timestamps
            timestamps = self._requests.get(client_id, [])
            # Filter to current window
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= self.max_requests:
                # Limit exceeded; calculate retry-after
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1.0, round((oldest_in_window + self.window_seconds) - now, 1))
                self._requests[client_id] = valid_timestamps
                return False, retry_after

            # Allow request
            valid_timestamps.append(now)
            self._requests[client_id] = valid_timestamps
            return True, 0.0

    def cleanup(self) -> None:
        """Removes client records that have no requests in the current window."""
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            stale_clients = [
                client for client, ts in self._requests.items()
                if not any(t > window_start for t in ts)
            ]
            for client in stale_clients:
                del self._requests[client]

    def reset(self) -> None:
        """Clears all rate limiting history."""
        with self._lock:
            self._requests.clear()
