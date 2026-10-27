"""Read provenance and checkpoints from Git objects, never a loose checkpoint."""

import subprocess
from pathlib import Path

from .canonical import strict_json
from .errors import RegistryError
from .store import REPO_ROOT

CHECKPOINT = "research/registry-checkpoint.json"


class GitCheckout:
    def __init__(self, root=REPO_ROOT):
        self.root = Path(root).resolve()

    def _run(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, check=True
        )
        return result.stdout

    def commit(self):
        return self._run("rev-parse", "HEAD").decode().strip()

    def clean(self):
        return not self._run(
            "status", "--porcelain", "--untracked-files=normal"
        ).strip()

    def committed(self, relative):
        # ls-tree distinguishes an absent object from a failed git invocation.
        if not self._run("ls-tree", "HEAD", "--", relative).strip():
            return None
        return self._run("show", f"HEAD:{relative}")


def committed_checkpoint(git):
    value = git.committed(CHECKPOINT)
    if value is None:
        return None
    try:
        return strict_json(value)
    except (ValueError, UnicodeError) as exc:
        raise RegistryError(
            "REGISTRY_CHECKPOINT_MISMATCH", "committed checkpoint"
        ) from exc
