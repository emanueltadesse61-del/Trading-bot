## T-006: Data build (pure functions) and holdout guard

**State:** Review — implemented by Codex; independent Claude review pending
**Phase:** 1   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** T-005 Accepted

### Goal
Implement `docs/data-spec.md` v1.1 §2–7 as pure functions, plus the §8.2 holdout-path guard, so that every case in `tests/fixtures/data_cases.json` passes.

### Inputs
- `docs/data-spec.md` (authoritative), `tests/fixtures/data_cases.json`
- `docs/portfolio-spec.md` §2 (the `compute_signals` contract that the output must satisfy)

### Outputs
- `trader/data/params.py`: frozen `DataParams` with `JUMP_LIMIT = 0.25` and `UNITS = {"GBP": 1.0, "GBX": 0.01}`. Add a frozen-values test alongside `test_params_frozen.py`.
- `trader/data/records.py`: frozen dataclasses `PriceRecord(instrument, date, close, unit)` and `DistributionRecord(instrument, ex_date, amount, unit)`, plus `JumpException(instrument, date, reason, approved)`.
- `trader/data/build.py`: `build_dataset(calendar, t, universe, prices, distributions, exceptions, params, mode="operational", exceptions_version=None) -> DataBuild`.
  - `DataBuild` (frozen): `dates: list[date]`, `tr_close: dict[str, list[float | None]]`, `trade_close: dict[str, float | None]`, `data_ok: bool`, `report: list[DataIssue]`, `mode`, `exceptions_version`, `exceptions_digest`.
  - `DataIssue(code, instrument, date)`, sorted by (instrument, date, code).
- `trader/data/holdout.py`: `check_holdout_path(path: Path, repo_root: Path, agent_workspaces: Sequence[Path]) -> None`, raising `HoldoutPathError` with code `HOLDOUT_PATH_FORBIDDEN` for anything inside the repo or any agent workspace. Real paths are resolved, including symlinks, before comparing. A sibling directory whose name merely starts with the repo name is **not** inside it.
- `tests/unit/test_data_cases.py`: one parametrised test per fixture case.

### Evidence
Not applicable (engineering of an accepted spec). `JUMP_LIMIT` is a judgement recorded in T-005.

### Constraints
- Pure functions: no I/O (except the holdout guard's path resolution), no clock, no network.
- The output of `build_dataset` must be accepted unchanged by `compute_signals`. Add one test that feeds a built dataset straight into `compute_signals`.
- Never fill, interpolate or carry forward a price.
- Do not edit fixtures; a mismatch goes through the disagreement process in `AGENTS.md`.

### Acceptance criteria
- [ ] Every `cases` entry except D14: `dates`, `tr_close`, `trade_close` within 1e-10; `data_ok`, `report`, `mode`, `exceptions_version`, `exceptions_digest` exact.
- [ ] D14: all six paths give the expected outcome.
- [ ] DV1–DV5 raise `InvalidInputError` with the expected code. Add `INVALID_EXCEPTIONS_VERSION` to `trader.errors.INPUT_ERROR_CODES`.
- [ ] Extra tests beyond the fixture: an empty universe; an instrument with no records at all (stale, not an error).
- [ ] Composition tests: (1) a record error on an **unheld** instrument gives `data_ok` false and `plan_orders` returns `BLOCKED_DATA`; (2) a **held** instrument that is only stale gives `data_ok` true, `missing_data` from `compute_signals`, and `BLOCKED_HELD_INELIGIBLE` from the planner.
- [ ] The built dataset feeds `compute_signals` without modification.
- [ ] CI green; `docs/handoff.md` updated.

### Exclusions
Parquet storage, manifests and any real-feed adapter (next card, T-007, which adds the `pyarrow` dependency). Backtesting (T-008). No downloads, no broker calls, no spending.

### Open questions
None, provided Codex's T-005 review raises no blocking findings.
