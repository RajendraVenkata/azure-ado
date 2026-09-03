from ado_migrate.mutation import DryRunGuard


class GitTransport(DryRunGuard):
    """Base for real (git subprocess) and fake GitTransport implementations.

    The real mirror clone/push operation is added here by ticket 04.
    """


class InMemoryFakeGitTransport(GitTransport):
    def __init__(self, dry_run: bool = False):
        super().__init__(dry_run)
        self.pushed: list[tuple[str, str]] = []

    def push_mirror(self, source_url: str, destination_url: str) -> None:
        def do_push() -> None:
            self.pushed.append((source_url, destination_url))

        self._mutate(f"push mirror {source_url} -> {destination_url}", do_push)
