# Backtest Specification (v1.0)

Status: **Review — awaiting Codex's requirements check (T-008).** Author: Claude. Last updated: 2026-10-16. Design choices that need review are collected in `docs/decisions/0009-backtest-simulator-design.md`.

This document defines how the daily simulator turns market records, a schedule and an order generator into fills, cash, daily equity and metrics. It reuses the accepted signal, target and planner code unchanged (`docs/portfolio-spec.md`) and the data layer (`docs/data-spec.md`). Reference cases: `tests/fixtures/backtest_cases.json`, computed by Claude's own calculator outside the repository (§11).

**Scope of v1.0 (T-008):** simulator, cost model, schedules, the strategy and baseline order generators, and per-run metrics, on **synthetic data**. **Not in scope:**
- Gate 3 statistics: paired monthly ΔSR, bootstrap, walk-forward windows;
- the experiment registry;
- loading open prices into raw datasets.

Each of those has its own later card (§12). No result from this simulator is evidence of an edge until the research protocol's pre-registration, registry and data prerequisites are met.

## 1. Parameters (`BacktestParams`)

Changing a cost or timing parameter is a new registered variant once real data is used. Strategy parameters stay in `Params` (portfolio spec §1).

| Name | Value | Meaning |
|---|---|---|
| `INITIAL_CASH` | 10,000.00 GBP | Settled cash at the start; no holdings (charter §4) |
| `COMMISSION_RATE` | 0.0005 | Per-order commission as a fraction of fill value (feasibility D4, IBKR UK Fixed) |
| `COMMISSION_MIN` | 3.00 GBP | Minimum per order, buys **and** sells (D4) |
| `SLIPPAGE` | 0.0005 | Per side, until measured paper fills replace it (protocol §5) |
| `HALF_SPREAD` | per instrument, required | Half the bid-ask spread as a fraction, per side. No default; a missing value is an input error |
| `COST_MULTIPLIER` | 1 (stress run: 2) | Multiplies `SLIPPAGE`, `HALF_SPREAD`, `COMMISSION_RATE` **and** `COMMISSION_MIN` (protocol §5, standards §3) |
| `SETTLEMENT_LAG` | 2 sessions | Net sale proceeds become settled cash at the open of the 2nd session after the fill session |
| `DISTRIBUTION_LAG` | 20 sessions | Distribution cash becomes settled 20 sessions after the ex-date. Assumption: the data has no pay dates (decision 0009) |
| `ANNUALISATION` | 252 | Sessions per year for metrics (same as `Params`) |

There is no commission maximum and no stamp duty in v1.0. Both are UNVERIFIED in the feasibility matrix and enter only by amendment. Cash earns 0% (protocol §5).

## 2. Inputs

### 2.1 Market records

- **`calendar`:** ordered exchange sessions, including the warm-up history before `start`. It must satisfy data spec §2 (strictly increasing, unique).
- **`start`, `end`:** sessions in `calendar`, with `start < end`. The backtest runs on sessions `start … end`; earlier sessions serve only as signal history.
- **Price records:** the canonical `PriceRecord` (data spec §2) gains one optional field, **`open`** (number or `None`, same `unit` as `close`, converted by the same GBX ÷ 100 rule).
  - `open` is the session's official opening price, **unadjusted**.
  - `open = None` means no open is known for that session.
  - Raw-dataset storage and CSV import are unchanged in v1.0: `write_raw_dataset` refuses any record with a non-`None` open (`DataStoreError("OPEN_PRICES_UNSUPPORTED", "prices")`) until a data card adds them to the raw-dataset schema (§12).
- **Distribution records** and **jump exceptions:** as in the data spec.
- **`universe`, `asset_class`, `HALF_SPREAD`:** for every instrument any generator may trade.

### 2.2 Input validation (before the first session)

`run_backtest` raises `BacktestInputError(code, detail)` and simulates nothing if:

| Code | Condition |
|---|---|
| `BACKTEST_CALENDAR` | `calendar` invalid, or `start`/`end` not sessions in it, or `start ≥ end` |
| `BACKTEST_DATA_EXCLUDED` | `build_dataset` at `t = end` (research mode, the supplied exceptions snapshot) reports any instrument-**excluding** code (data spec §3) for an instrument in the universe |
| `BACKTEST_OPEN` | An `open` that is not `None` is non-finite or ≤ 0 (after unit conversion) |
| `BACKTEST_SPREAD` | A tradable instrument has no `HALF_SPREAD`, or one that is non-finite or < 0 |
| `BACKTEST_PARAMS` | A parameter outside its type or range (non-negative costs, `COST_MULTIPLIER` > 0, integer lags ≥ 0, positive `INITIAL_CASH`) |

Data flags that only make `data_ok` false (`DATA_JUMP`, `DATA_STALE`) are **not** input errors. They block decisions at the dates they affect (§6).

## 3. The session loop

For each session `d` from `start` to `end`, in order:

1. **Settle.** Every unsettled lot whose settlement session is `d` or earlier moves to settled cash.
2. **Distributions.** For each instrument with a distribution whose `ex_date = d`: the entitled shares are the holding **at the start of `d`**, before this session's fills. Cash = shares × amount in GBP. It is added as an unsettled lot settling at `d + DISTRIBUTION_LAG` sessions. Shares bought at `d`'s open are **not** entitled.
3. **Fills at the open.** Orders produced at the previous session's decision are executed (§4): all sells first, then all buys, each group in ascending `id`. Orders live for exactly one session; nothing is carried forward.
4. **Valuation at the close.**
   - `NAV_d = settled + Σ unsettled lots + Σ_i q_i × close_i`, where `close_i` is the unadjusted close at `d` in GBP.
   - If an instrument is held and has no close at `d`, its last known close is used and the instrument is listed as `stale` for `d`.
5. **Decision.** If `d` is a decision session (§5) **and** `d < end`, the generator receives the state at the close of `d` and returns orders to fill at the next session's open. No decision is made at `end`, because its orders could never fill inside the run.

On `start` there are no fills and no lots, so `NAV_start = INITIAL_CASH`.

## 4. Fills and costs

Let `m = COST_MULTIPLIER`, `o` = the open at the fill session in GBP, and `c_i = m × (HALF_SPREAD_i + SLIPPAGE)`.

| Step | Sell | Buy |
|---|---|---|
| No open (`None`) | Cancelled: `NO_PRICE` | Cancelled: `NO_PRICE` |
| Quantity | `q = min(ordered, held)`. If `q = 0`: cancelled, `NO_HOLDING`, no commission | The largest `q ≤ ordered` whose cost ≤ settled cash (below) |
| Fill price | `f = o × (1 − c_i)` | `f = o × (1 + c_i)` |
| Commission | `C = max(m × COMMISSION_MIN, m × COMMISSION_RATE × q × f)` | Same formula |
| Cash | `net = q × f − C`. If `net ≥ 0`, it becomes an unsettled lot settling at `d + SETTLEMENT_LAG`. If `net < 0`, the shortfall is debited from settled cash **now** | `q × f + C` is debited from settled cash |
| Status | `OK`, or `SHORTFALL` if settled cash is negative after the fill | `OK`, `CASH_LIMITED` (`0 < q < ordered`), or `SKIPPED_CASH` (`q = 0`, nothing debited) |
| Cost recorded | `spread_slippage_cost = q × (o − f)` | `q × (f − o)` |

**Buy affordability.** Start from `q = min(ordered, floor(settled / f))`. While `q > 0` and `q × f + C(q) > settled + 1e-9`, reduce `q` by 1. This is the largest affordable quantity. It handles a gap-up open the planner could not see (the planner sized the order on the previous close with `BUY_BUFFER`). Buys are processed in ascending `id`, so earlier buys can use up the cash for later ones.

**Exits are never blocked.** A sell always executes when there is an open and a holding, even if the commission minimum makes its net proceeds negative. Settled cash may then go below zero; the session is flagged `settled_negative`. The planner treats negative settled cash as invalid input (`INVALID_CASH`), so the strategy records `BLOCKED_INVALID_INPUT` and places no orders until settled cash is ≥ 0 again. Baselines likewise make no buys while it is negative.

No order may exceed one session's life, partially fill for liquidity reasons, or trade fractional shares.

## 5. Schedules

| Schedule | Decision sessions |
|---|---|
| `weekly` (strategy primary) | The last session of each ISO week (ISO year + week number) in `calendar`. A Friday holiday moves it to Thursday; the ISO week spanning New Year is one week |
| `monthly` (strategy robustness variant; all baselines) | The last session of each calendar month in `calendar` |

A session counts only if the **next** session in `calendar` exists and falls in a later period. The final supplied session is never a decision session, because whether its period has ended is unknown. Only sessions in `start … end − 1` are used (§3 step 5).

## 6. Order generators

A generator is a function `(d, state, market) → orders | status`. `state` holds holdings, settled cash, unsettled cash and NAV at the close of `d`. Every decision records its `status` (`OK`, or the `BLOCKED_*` code), its orders, and for the strategy its `TargetResult` diagnostics.

### 6.1 Strategy

At decision `d`:
1. `build_dataset(calendar up to d, t = d, universe, …)` in research mode, giving `dates`, `tr_close`, `trade_close`, `data_ok`.
2. `compute_signals` → `compute_targets` → `plan_orders`, unchanged. `AccountState`:
   - `holdings`;
   - `cash_settled` and `cash_unsettled` from `state`;
   - `open_orders = False`, because every order has filled or been cancelled by the next close;
   - `reconciliation_clean = True`;
   - `data_ok` from step 1.
3. Prices are `trade_close` at `d`. An `InvalidInputError` is caught and recorded as `BLOCKED_INVALID_INPUT` with its code; no orders. A planner `BLOCKED_*` status is recorded; no orders.

### 6.2 Baseline rebalancer

Baselines use one simple rebalancer, **not** the strategy planner. The planner's volatility ceiling would block a 60/40 portfolio, and baselines have no ceiling. Given target weights `w`, at decision `d`:
- If `data_ok` is false for the baseline's instruments, record `BLOCKED_DATA`; no orders.
- `NAV` as in §3.4. Actual weights `a_i = q_i P_i / NAV`, with `P_i = trade_close` at `d`.
- Instruments with no `P_i` at `d` are **not traded**: never sold or bought for missing data.
- Trade set: `|a_i − w_i| > BAND + TOL`, or `w_i = 0` and `q_i > 0`. Target shares `q*_i = floor(w_i × NAV / P_i + FLOOR_EPS)`.
- Settled-cash limit exactly as portfolio spec §6.3 step 5 (`BUY_BUFFER`, `COMMISSION_RESERVE` per buy, scale factor `k`, floor).
- Drop zero deltas. Sells first, then buys, each in ascending `id`.

`BAND`, `TOL`, `FLOOR_EPS`, `BUY_BUFFER` and `COMMISSION_RESERVE` are taken from `Params`.

### 6.3 Baselines (protocol §5)

All baselines use the `monthly` schedule, the same cost model and the same `INITIAL_CASH`.

| Baseline | Targets at each decision |
|---|---|
| **60/40 (deciding)** | VWRL 0.60, VGOV 0.40 |
| **Global equity** | VWRL 1.00. Monthly band rebalancing means distributions and settled cash are reinvested once the drift exceeds the band |
| **10-month moving-average rule** | For each of the N strategy-universe instruments: if `tr_close` at `d` is above the mean of `tr_close` at the last 10 `monthly`-schedule sessions in `calendar` up to and including `d` (warm-up month-ends before `start` count), the target is `1/N`; otherwise 0. If any of those 10 values is missing, or fewer than 10 exist, the instrument is not traded at `d` |
| **Cash** | No orders; NAV stays at `INITIAL_CASH` |

The baselines are configured with explicit instrument ids. In synthetic tests they run on `SYN_` instruments.

## 7. Outputs (`BacktestResult`)

- **Daily ledger:** per session: settled, unsettled, holdings, NAV, stale instruments, the `settled_negative` flag, fills (kind, instrument, qty, fill price, commission, spread/slippage cost, status), cancellations (instrument, side, qty, reason), and distributions (instrument, shares, cash).
- **Decisions:** per decision session: status, orders and diagnostics.
- **Metrics** (§8), and totals: commission, spread/slippage cost, distributions received, number of fills of each status.
- **Inputs echo:** `start`, `end`, schedule, `BacktestParams`, generator name, and the exceptions version and digest used.

## 8. Metrics

Using the daily NAV series `N_0 … N_T` (`N_0` = the close of `start`) and returns `r_k = N_k / N_{k−1} − 1`:

| Metric | Definition |
|---|---|
| `ann_return` | `(N_T / N_0)^(252 / T) − 1` |
| `ann_vol` | `stdev(r, ddof = 1) × √252` |
| `sharpe` | `mean(r) / stdev(r, ddof = 1) × √252`, risk-free 0. `None` if the stdev is 0 |
| `max_drawdown` | `max_k (1 − N_k / max_{j ≤ k} N_j)` |
| `max_drawdown_sessions` | The longest stretch, in sessions, from a running peak to any later session still below it |
| `monthly_returns` | For each calendar month in the run: NAV at the last session of that month ÷ the previous month's value − 1. The first month uses `N_0`; the final, possibly partial, month ends at `end` |
| `turnover` (annual) | `Σ |q × f| over all fills / (2 × mean(N)) × 252 / T` |
| `cost_drag` (annual) | `(Σ commission + Σ spread/slippage cost) / mean(N) × 252 / T` |

These are run-level descriptions. Gate 3 uses paired monthly returns and its own statistics (protocol §6), specified in a later card.

## 9. Required properties (tests in addition to §11)

1. **No look-ahead.** Changing any price, open or distribution dated after `d` leaves every decision at `d` (status, orders, diagnostics) unchanged. Changing the open at `d + 1` changes only that session's fills and later values.
2. **Cash identity.** At every session: `settled + unsettled = INITIAL_CASH + Σ net sale proceeds + Σ distributions − Σ buy costs`, using the recorded fills (tolerance 1e-9 × scale).
3. **NAV identity.** `NAV = settled + unsettled + Σ q × last close` at every session.
4. **Settled cash** never goes below 0 except through a `SHORTFALL` sell, and the strategy places no orders while it is negative.
5. **Determinism.** The same inputs give an identical `BacktestResult`.
6. **Shared logic.** The strategy generator calls the accepted `compute_signals`, `compute_targets` and `plan_orders`. No copy of their logic exists in the backtest package.
7. **Holdings never go negative.** No fractional shares; no order survives past its fill session.

## 10. Reporting anomalies

A backtest whose ledger ever shows `settled_negative`, `stale` valuations or blocked decisions is still a valid **record**, but those counts must be reported with any metric (§7 totals). Nothing is hidden or silently repaired.

## 11. Reference cases (`tests/fixtures/backtest_cases.json`)

Produced by Claude's independent calculator; tolerance 1e-12 relative, 1e-9 absolute. Simulator cases use **scripted orders**: a test generator returns the listed orders at the listed decision dates. This isolates fills, cash and valuation from the strategy.

| Case | Exercises | Key expected result |
|---|---|---|
| BT1_buy_fill_and_valuation | Fill at the next open with spread and slippage; GBX ÷ 100; minimum commission; close valuation | SYN_A 50 @ 100.15, commission 3.00; SYN_B 100 @ £20.05; settled 2,981.50; NAV 10,041.50 then 10,071.50 |
| BT2_settlement_lag | T+2 settlement of sale proceeds | Sale at Wed open; Thu buy limited to 9 shares (`CASH_LIMITED`); Fri buy of 100 filled after settlement |
| BT3_distribution_entitlement | Ex-date entitlement at the start of the session; GBX amount; distribution lag | 40 shares × £0.50 = £20 unsettled; the 10 shares bought at the ex-date open get nothing |
| BT4_gap_up_cash_limited | Largest affordable quantity incl. commission; ascending-id buy order | SYN_A 99 → 95; SYN_B 20 → 9; SYN_C `SKIPPED_CASH`; settled 7.09759 |
| BT5_missing_open_and_close | `NO_PRICE` cancellation; stale valuation | SYN_B order cancelled; SYN_A valued at 101 on Wed and listed stale |
| BT6_min_commission_shortfall | A sale whose commission exceeds its proceeds | Net −2.0005; settled −1.991; `SHORTFALL`; `settled_negative` |
| BT7_cost_multiplier_2x | Every cost component doubled | Fill 100.30; commission 6.00 |
| BT8_schedules | ISO-week and month ends with holidays and a year boundary | Weekly: 2025-12-19, 12-24, 2026-01-02, 01-09, 01-16, 01-23, 01-29; monthly: 2025-12-31, 2026-01-29; the final session is never included |
| RB1–RB4 | Baseline rebalancer | Band trades with `k` scaling (15 VWRL, 238 VGOV); unsettled cash unusable (1 VGOV); inside the band no trade; exit and no trade on a missing price |
| MT1_metrics | Metric definitions | Values in the fixture, cross-checked by a second independent computation |

## 12. Later cards (dependencies)

| Card | Content | Needed before |
|---|---|---|
| Data: open prices in raw datasets | Raw-dataset schema v2 with `open`; CSV column; T-007 split and reader updated | Any backtest on real data |
| Gate 3 statistics | Paired monthly ΔSR, stationary block bootstrap, walk-forward windows by calendar year, simpler-rule test | Any Gate 3 result |
| Experiment registry | SQLite append-only rows (protocol §2), with code commit (clean-checkout rule), config hash, dataset ids and manifest digests | Any run on real data |
| Pre-registration | `research/hypotheses/H-001…H-003` (primary and two comparisons, decision 0008) | Any run on real data |
