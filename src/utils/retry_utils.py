"""
Retry and timeout utilities for API and HTTP calls.
Used by mock API client, REST Countries, and scraper.
"""
import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    timeout_sec: float | None = None,
    backoff_sec: float = 1.0,
    allowed_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """
    Execute fn(); on failure retry up to max_retries with exponential backoff.
    If timeout_sec is set, each attempt is limited by that (caller must enforce in fn).
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except allowed_exceptions as e:
            last_exc = e
            if attempt == max_retries:
                raise
            sleep = backoff_sec * (2**attempt)
            logger.warning("Attempt %s failed: %s. Retrying in %.1fs.", attempt + 1, e, sleep)
            time.sleep(sleep)
    raise last_exc  # type: ignore[misc]
