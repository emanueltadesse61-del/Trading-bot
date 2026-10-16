import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_IMPORTS = frozenset({"openai", "anthropic"})


def assert_no_forbidden_imports(source, filename="<source>"):
    for node in ast.walk(ast.parse(source, filename=filename)):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules = [node.module or ""]
        else:
            continue
        for module in modules:
            assert module.split(".")[0] not in FORBIDDEN_IMPORTS, (
                f"{filename}:{node.lineno}: forbidden import {module}"
            )


def test_source_has_no_forbidden_imports():
    for path in sorted((ROOT / "src").rglob("*.py")):
        assert_no_forbidden_imports(path.read_text(), str(path.relative_to(ROOT)))


def test_live_configuration_absent():
    assert not (ROOT / "config/live").exists(), "Live configuration is not authorised"


@pytest.mark.parametrize("module", sorted(FORBIDDEN_IMPORTS))
@pytest.mark.parametrize("template", [
    "import {module}", "import {module} as client", "import os, {module}",
    "from {module} import Client", "from {module}.client import Client",
    "def run():\n    import {module}",
])
def test_guard_rejects_forbidden_imports(module, template):
    with pytest.raises(AssertionError, match="forbidden import"):
        assert_no_forbidden_imports(template.format(module=module))


@pytest.mark.parametrize("source", [
    "import numpy as np", "from pandas import DataFrame",
    "# import openai", 'message = "import anthropic"',
])
def test_guard_accepts_permitted_source(source):
    assert_no_forbidden_imports(source)
