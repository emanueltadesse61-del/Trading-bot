## T-001: Repository bootstrap

**State:** Ready
**Phase:** 0   **Author:** Claude   **Implementer:** Codex
**Depends on:** none

### Goal
Turn the bootstrap documents into a working Python project skeleton with locked dependencies, tests and CI, with no trading logic.

### Inputs
- `docs/architecture.md` §2 (package layout) and §7 (stack)
- `AGENTS.md` (hard rules)
- `tests/fixtures/portfolio_cases.json` (must load in a smoke test)

### Outputs
- `pyproject.toml` for package `trader` (src layout), Python 3.12, managed with **uv**; committed `uv.lock`.
- Runtime dependencies: `numpy`, `pandas`. Dev dependencies: `pytest`, `ruff`.
- Empty subpackages with a one-line docstring each: `trader.data`, `trader.signals`, `trader.portfolio`, `trader.planner`, `trader.risk`, `trader.backtest`, `trader.execution`, `trader.monitor`, `trader.registry`.
- `tests/unit/test_smoke.py`:
  - imports every subpackage;
  - loads `tests/fixtures/portfolio_cases.json` and asserts the 10 case names listed in `docs/portfolio-reference-cases.md`.
- `tests/unit/test_guards.py`:
  - fails if any file under `src/` imports `openai`, `anthropic`, or any module named in a `FORBIDDEN_IMPORTS` list in the test;
  - fails if a `config/live/` directory exists.
- `.github/workflows/ci.yml`: on push and pull request, run `uv sync --locked`, `uv run ruff check .`, `uv run pytest -q`.
- `.gitignore`: `data/`, `*.sqlite`, `*.db`, `.env*`, `__pycache__/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`.
- `README.md`: one paragraph on the project, how to run tests, and a pointer to `docs/handoff.md` and `AGENTS.md`.

### Constraints
- No broker connection code, no network calls, no market data, no strategy logic.
- Do not modify anything under `docs/` except `docs/handoff.md`, and do not edit `tests/fixtures/`.

### Acceptance criteria
- [ ] `uv sync --locked && uv run ruff check . && uv run pytest -q` passes locally; output summary pasted in the PR.
- [ ] CI runs green on the PR.
- [ ] Guard tests fail when a forbidden import is added (show this once in the PR with a throwaway commit or a parametrised test).
- [ ] `docs/handoff.md` updated: T-001 commit recorded, CI status as a completed check.

### Exclusions
Docker, pre-commit hooks, type-checking tools, any `config/` content, dashboards.

### Open questions
None.
