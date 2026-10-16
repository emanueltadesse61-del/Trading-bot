"""Path containment only; passing this check never authorises holdout access."""

from collections.abc import Sequence
from pathlib import Path


class HoldoutPathError(ValueError):
    code = "HOLDOUT_PATH_FORBIDDEN"

    def __init__(self) -> None:
        super().__init__(self.code)


def check_holdout_path(path: Path, repo_root: Path, agent_workspaces: Sequence[Path]) -> None:
    destination = Path(path).resolve()
    for root in (repo_root, *agent_workspaces):
        if destination.is_relative_to(Path(root).resolve()):
            raise HoldoutPathError()
