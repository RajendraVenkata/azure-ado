import time
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class TransientError(Exception):
    """Raised for retryable failures (rate limiting, network errors)."""


@dataclass
class MutationRecord:
    description: str
    executed: bool


class DryRunGuard:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.mutation_log: list[MutationRecord] = []
        self._pending_failures: list[Exception] = []

    def queue_failure(self, exception: Exception) -> None:
        self._pending_failures.append(exception)

    def _mutate(
        self,
        description: str,
        fn: Callable[[], T],
        max_attempts: int = 3,
        backoff_seconds: float = 0.0,
    ) -> Optional[T]:
        if self.dry_run:
            self.mutation_log.append(MutationRecord(description, executed=False))
            return None

        attempt = 0
        while True:
            attempt += 1
            try:
                if self._pending_failures:
                    raise self._pending_failures.pop(0)
                result = fn()
                self.mutation_log.append(MutationRecord(description, executed=True))
                return result
            except TransientError:
                if attempt >= max_attempts:
                    self.mutation_log.append(MutationRecord(description, executed=False))
                    raise
                time.sleep(backoff_seconds)
                continue
            except Exception:
                self.mutation_log.append(MutationRecord(description, executed=False))
                raise
