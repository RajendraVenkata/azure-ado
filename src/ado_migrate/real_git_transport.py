"""Real git-backed GitTransport.

Deliberately excluded from the automated test suite (see spec
ado-real-client-seeder, ticket 02) — every call here shells out to a real
`git` process against real remote URLs. Verification of this module is
manual — run it against a real Azure DevOps organization.
"""

import base64
import subprocess
import tempfile
from typing import Optional

from ado_migrate.git_transport import GitTransport
from ado_migrate.mutation import TransientError

_TRANSIENT_MARKERS = (
    "could not resolve host",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
    "temporary failure",
    "the remote end hung up unexpectedly",
)


class RealGitTransport(GitTransport):
    def __init__(self, pat: str, dry_run: bool = False):
        super().__init__(dry_run)
        self._pat = pat

    def push_mirror(self, source_url: str, destination_url: str) -> None:
        def do_push() -> None:
            with tempfile.TemporaryDirectory() as tmp_dir:
                self._run_git(["clone", "--mirror", source_url, tmp_dir])
                self._run_git(["push", "--mirror", destination_url], cwd=tmp_dir)

        self._mutate(f"push mirror {source_url} -> {destination_url}", do_push)

    def _run_git(self, args: list[str], cwd: Optional[str] = None) -> None:
        auth_header = f"Authorization: Basic {_basic_auth_header(self._pat)}"
        command = ["git", "-c", f"http.extraHeader={auth_header}", *args]

        try:
            subprocess.run(
                command, cwd=cwd, check=True, capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired as exc:
            raise TransientError(str(exc)) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").lower()
            # git doesn't give a structured error code, so this is a
            # best-effort substring match on common transient-failure
            # wording. When we can't tell, treat it as persistent rather
            # than risk silently retrying a genuine (non-transient) error.
            if any(marker in stderr for marker in _TRANSIENT_MARKERS):
                raise TransientError(exc.stderr) from exc
            raise


def _basic_auth_header(pat: str) -> str:
    return base64.b64encode(f":{pat}".encode()).decode()
