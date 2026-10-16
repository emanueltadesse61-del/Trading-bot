"""Path containment only; passing this check never authorises holdout access."""

import os
from collections.abc import Sequence
from pathlib import Path


class HoldoutPathError(ValueError):
    code = "HOLDOUT_PATH_FORBIDDEN"

    def __init__(self) -> None:
        super().__init__(self.code)


def check_holdout_path(path: Path, repo_root: Path, agent_workspaces: Sequence[Path]) -> None:
    destination = Path(path).resolve()
    for root in (repo_root, *agent_workspaces):
        resolved_root = Path(root).resolve()
        if destination.is_relative_to(resolved_root):
            raise HoldoutPathError()
        # Resolve does not necessarily canonicalise case on case-insensitive
        # filesystems. Identity also catches aliases while allowing new leaves.
        for ancestor in (destination, *destination.parents):
            try:
                same = os.path.samefile(ancestor, resolved_root)
            except (FileNotFoundError, NotADirectoryError):
                continue
            # Other errors (e.g. denied access) propagate: do not assert safety
            # when filesystem identity cannot be checked.
            if same:
                raise HoldoutPathError()
