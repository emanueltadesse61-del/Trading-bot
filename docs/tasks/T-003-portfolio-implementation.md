## T-003: Synthetic portfolio implementation

**State:** Draft — becomes Ready when T-002 is Accepted
**Phase:** 0   **Author:** Claude   **Implementer:** Codex
**Depends on:** T-001 merged; T-002 (spec v1.2) Accepted

### Goal
Implement `docs/portfolio-spec.md` §3–§6 as pure functions that reproduce every case in `tests/fixtures/portfolio_cases.json`.

### Inputs
- `docs/portfolio-spec.md` (authoritative)
- `tests/fixtures/portfolio_cases.json`, `docs/portfolio-reference-cases.md`

### Outputs
- `trader/params.py`: frozen dataclass `Params` with every value in spec §1 as defaults.
- `trader/errors.py`: `InvalidInputError(code: str, detail: str)` with the codes in spec §2.1.
- `trader/signals/`: `compute_signals(dates: Sequence[datetime.date], tr_close: Mapping[str, Sequence[float | None]], params: Params) -> Signals`.
  - `dates`: the session calendar ending at t. Each series has exactly one value per date; `None`/NaN = missing. No alignment or re-indexing (spec §2, §3).
  - `Signals` (frozen dataclass): `eligible: frozenset[str]`, `ineligible_reason: dict[str, str]` (`insufficient_history` | `missing_data` | `min_vol`, spec §3 order), `trend_score`, `momentum_return`, `sigma` (dict per eligible id), `cov` (DataFrame over eligible ids, sorted).
- `trader/portfolio/`: `compute_targets(signals: Signals, asset_class: dict[str, str], params: Params) -> TargetResult` with `weights` (every id in `asset_class`, 0 for ineligible), `cash`, and diagnostics named as in the fixture (`ranking`, `top_n`, `w_trend`, `w_mom`, `combined`, `after_asset_cap`, `after_class_cap`, `sigma_p_before_scale`, `scale`). It re-applies the `MIN_VOL` rule defensively.
- `trader/planner/`: `plan_orders(targets: TargetResult, state: AccountState, prices: dict[str, float], cov: pandas.DataFrame, asset_class: dict[str, str], eligible: frozenset[str], params: Params) -> PlanResult`.
  - `AccountState`: `holdings: dict[str, int]`, `cash_settled`, `cash_unsettled`, `open_orders: bool`, `reconciliation_clean: bool`, `data_ok: bool`.
  - `PlanResult`: `status` (`OK`, `BLOCKED_OPEN_ORDERS`, `BLOCKED_RECONCILIATION`, `BLOCKED_DATA`, `BLOCKED_UNKNOWN_HOLDING`, `BLOCKED_HELD_INELIGIBLE`, `BLOCKED_NAV`, `BLOCKED_CONSTRAINTS`), checks run in spec §6.1 order, `orders` (list of `Order(id, side, qty, ref_price, reasons: tuple[str, ...])`), `nav`, `actual`, `passes` (per-iteration diagnostics: delta, buy_need, k, post weights, post vol, violations).
- `tests/unit/test_portfolio_cases.py`: one parametrised test per fixture case.

### Constraints
- Pure functions: no I/O, no clocks, no randomness, no network.
- All comparisons use `params.TOL`; all share counts use `floor(x + FLOOR_EPS)`.
- Weight-case tests build `Signals` directly from the fixture `inputs`: covariance = outer(vol_252d) × correlation (unlisted pairs 0; diagonal 1), or the explicit `covariance` matrix when given (W8).
- The S1 test passes the fixture `dates` and series as given; `null` becomes `None`/NaN.
- Invalid-input cases (`invalid` group) assert `InvalidInputError` with the expected code, raised by the function named in `stage`.
- Order-case tests take targets, classes and covariance from the case named in `targets_from`.
- Do not edit fixtures. A mismatch goes to `docs/decisions/` via the disagreement process in `AGENTS.md`.

### Acceptance criteria
- [ ] All weight cases: every expected weight, cash and diagnostic within 1e-8.
- [ ] Order cases: `status` and the order list (id, side, qty, set of reasons, order sequence) match exactly; where present, `nav`, `actual`, `buy_need` and `k` within 1e-8; O2 shows exactly two passes; O9 blocks after one pass.
- [ ] S1: eligibility and reasons exact (including STALE and GAP as `missing_data`); R63, R126, R252, trend score, momentum return, σ and covariance within 1e-8.
- [ ] Invalid cases V1–V9 raise `InvalidInputError` with the expected code.
- [ ] Every portfolio volatility (targets, actual, post-trade) goes through one `σ(x)` function implementing spec §2.2; W8 gives σp = 0.
- [ ] Leakage test: compute signals with `dates[:n]` and each series cut to n values; then change any value at a position ≥ n in the full series and recompute with the same cut. Outputs must be identical. A test must also show that passing a series longer than `dates` raises `INVALID_CALENDAR`.
- [ ] Property tests (no external library needed): for random valid inputs with a fixed seed, final weights respect both caps and the vol ceiling within TOL, cash ≥ 0, and weights are never scaled up.
- [ ] CI green; `docs/handoff.md` updated.

### Exclusions
Downloaded market data, backtests, cost models, broker code, parameter changes.

### Open questions
None, provided Codex's T-002 review raises no blocking findings.
