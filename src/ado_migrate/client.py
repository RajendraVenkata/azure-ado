from typing import Optional

from ado_migrate.mutation import DryRunGuard


class AdoClient(DryRunGuard):
    """Base for real (SDK/REST-backed) and fake AdoClient implementations.

    Concrete artifact-type operations (create_repo, create_work_item, ...)
    are added here incrementally by later tickets.
    """


class InMemoryFakeAdoClient(AdoClient):
    def __init__(self, dry_run: bool = False):
        super().__init__(dry_run)
        self.created: list[str] = []

    def create_placeholder(self, name: str) -> Optional[str]:
        def do_create() -> str:
            destination_id = f"dest-{name}"
            self.created.append(destination_id)
            return destination_id

        return self._mutate(f"create placeholder '{name}'", do_create)
