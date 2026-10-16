## T-008: Backtest simulator, cost model, baselines and run metrics (synthetic)

**State:** Review, v3 (Codex findings B1–B7 resolved; decision 0009 re-review sections). **Codex re-checks before building.**
**Phase:** 1 → 2   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** PR #12 (T-007 implementation), merged as `0805908`; `docs/backtest-spec.md` v1.2 and decision 0009 (this PR).

### Goal
A deterministic daily simulator that executes the accepted strategy code, and the protocol's baselines, with realistic fills, costs, settlement and distributions, and reports per-run metrics. It is verified entirely on synthetic data.

This card tests the **machinery, not the strategy**. Testing for an edge needs the pre-registration, the experiment registry, Gate 3 statistics and approved development data, each in its own later card (spec §12).

### Inputs
- `docs/backtest-spec.md` v1.2 (the authority) and `tests/fixtures/backtest_cases.json` (Claude's reference values)
- `docs/portfolio-spec.md` v1.3 and `trader.signals`, `trader.portfolio`, `trader.planner`, all unchanged
- `docs/data-spec.md` v1.2.1 and `trader.data`
- Decision 0009; protocol §4–5; backtesting standards §2–3
- Claude's T-007 review notes N1–N6 (PR #12)

### Outputs
1. **`PriceRecord.open`**: optional, default `None`, unit-converted like `close` (spec §2.1).
   - Existing callers and fixtures are unchanged.
   - `write_raw_dataset` raises `DataStoreError("OPEN_PRICES_UNSUPPORTED", "prices")` for any non-`None` open.
   - CSV import is unchanged: no `open` column; a file with one is still `IMPORT_BAD_HEADER`.
2. **`trader/backtest/` package:**
   - `params.py`: `BacktestParams` (spec §1), frozen, validated (`BACKTEST_PARAMS`).
   - `errors.py`: `BacktestInputError(code, detail)` with the spec §2.2 codes, plus `BACKTEST_ORDER` (spec §4).
   - `schedule.py`: `decision_sessions(calendar, kind)` for `weekly` and `monthly` (spec §5).
   - `adapter.py`: the point-in-time inputs of spec §2.3, used by both admission and every decision build, plus the whole-snapshot exceptions fingerprint.
   - `simulator.py`: `run_backtest(market, generator, params, *, start, end, schedule | decision_dates)` → `BacktestResult` (spec §2.2–§4, §7). `decision_dates` is an explicit sorted list for tests and the fixture's scripted cases, validated by `BACKTEST_SCHEDULE`. Every generator order is validated (`BACKTEST_ORDER`).
   - `generators.py`:
     - `strategy_generator(universe, asset_class, params, exceptions, exceptions_version)` (spec §6.1);
     - `rebalance(targets, state, prices, params)` (spec §6.2);
     - baselines `sixty_forty`, `global_equity`, `moving_average_10m`, `cash` (spec §6.3);
     - `scripted(orders_by_date)` for tests.
   - `metrics.py`: spec §8, including the undefined-metric reasons.
3. **Data spec §10:** apply the amendment in decision 0009.
4. **T-007 follow-ups** (from Claude's PR #12 review):
   - **N1:** `trader-split` refuses to run from a checkout with uncommitted changes to tracked files (`git status --porcelain --untracked-files=no` non-empty), exit 1 with `SPLIT_DIRTY_CHECKOUT`.
   - **N2:** `read_raw_dataset` also maps `pyarrow.ArrowException` to `DATASET_MANIFEST_MISMATCH`.
   - **N3:** a real unreadable-file test (`chmod 000`, skipped when running as root) proving a clean failure with nothing published.
   - **N4:** `preflight` collects every leftover (existing outputs and staging directories) into one error, listing all paths. Use `SPLIT_OUTPUT_EXISTS` if any output exists, otherwise `SPLIT_STAGING_EXISTS`.
   - **N5 and N6:** README states "UTF-8 without BOM" and lists `SPLIT_PARTITION_MISMATCH` and `SPLIT_DIRTY_CHECKOUT`.

### Evidence
Not applicable for the design (engineering; choices recorded in decision 0009). The reference values come from Claude's independent calculator; the metric case is also cross-checked by a second computation.

### Constraints
- Synthetic data only. No network, no broker, no real or holdout data. Instrument ids in tests start with `SYN_`, except rebalancer cases using the fixture's ids.
- The strategy generator must call the existing `compute_signals`, `compute_targets` and `plan_orders`. No reimplementation (spec §9.6).
- No result produced here is reported as performance evidence.

### Acceptance criteria
- [ ] **Fixture:** every `simulator_cases` entry reproduces every session's settled, unsettled, holdings, NAV, stale list, `settled_negative`, fills (qty, fill price, commission, spread/slippage cost, status), cancellations and distributions within the fixture tolerance, using `scripted` orders at the given decision dates.
- [ ] **Fixture:** `schedule_case` weekly and monthly lists match exactly. `rebalancer_cases` orders match exactly. `metric_cases` MT1–MT5 match within tolerance, including `None` values, `undefined` reasons and `insolvent_on`. Every `invalid_input_cases` entry BV1–BV8 raises its code.
- [ ] **Admission:**
  - each spec §2.2 code is raised by a test;
  - `BACKTEST_DATA_EXCLUDED` is triggered by a duplicate price for one run instrument;
  - the same duplicate dated **after** `end`, or in an instrument outside the run's set (e.g. VWRL in a strategy run), does **not** refuse the run.
- [ ] **Point-in-time adapter (spec §2.3):**
  - an exception entry dated after `d` neither blocks nor changes the decision at `d`;
  - the run fingerprint equals the data spec digest of the whole snapshot;
  - decision builds receive no record dated after `d`.
- [ ] **Properties (spec §9):**
  - no look-ahead, between two **admitted** inputs: perturb a price, an open, a distribution and an exception entry after `d`, and the decisions at `d` are identical;
  - cash identity and NAV identity at every session;
  - no buy ever has a negative quantity: a valid BUY after a `SHORTFALL`, in the same fill session and the next, is `SKIPPED_CASH` (BT12);
  - determinism;
  - non-negative holdings.
- [ ] **Strategy end-to-end (synthetic):** a 2-instrument history of ≥ 300 sessions, built so the planner returns orders, runs weekly and monthly. Decisions record `OK` with orders. A session with an unapproved jump records `BLOCKED_DATA` and no orders. A shortfall makes the next decision `BLOCKED_INVALID_INPUT` (`INVALID_CASH`).
- [ ] **Baselines (synthetic):**
  - 60/40 and global equity trade on the first monthly decision and then only on band breaches;
  - the moving-average rule holds an instrument above its 10-month average and exits it when it falls below;
  - an instrument with fewer than 10 usable month-ends is not traded, and is neither sold nor bought even if held;
  - cash NAV is constant.
- [ ] **Cost stress:**
  - BT7 (buy) and BT11 (sell) hold;
  - for a fixed open, side and quantity at m = 1 and m = 2, the fill equals the spec §4 formula (buys worsen upward, sells worsen downward), spread/slippage cost = `q × |f − o|` scales with m, and commission = `max(m × MIN, m × RATE × q × f)`;
  - no monotonic assertion on fill price, commission or aggregate cost across the parameter domain (commission is charged on the changed notional, and doubling can prevent fills); the changed fills and turnover are reported.
- [ ] **Open field:** existing data, T-006 and T-007 tests pass unchanged. `write_raw_dataset` refuses a record with an open.
- [ ] **Follow-ups:** N1–N6 implemented with tests (N1 via a temporary git repo in the test).
- [ ] CI green; `docs/handoff.md` updated.

### Exclusions
Gate 3 statistics, bootstrap, walk-forward windows, experiment registry, pre-registration files, raw-dataset schema v2 or CSV `open` column, real or holdout data, broker adapter, risk gate, FX, intraday.
