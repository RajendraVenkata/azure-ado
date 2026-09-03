from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


@dataclass
class MutationRecord:
    description: str
    executed: bool


class DryRunGuard:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.mutation_log: list[MutationRecord] = []

    def _mutate(self, description: str, fn: Callable[[], T]) -> Optional[T]:
        if self.dry_run:
            self.mutation_log.append(MutationRecord(description, executed=False))
            return None

        result = fn()
        self.mutation_log.append(MutationRecord(description, executed=True))
        return result
