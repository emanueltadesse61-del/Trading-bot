# Backtest Specification (v1.2.1)

Status: **Review — v1.2 awaiting Codex's re-check (T-008).** Author: Claude. Last updated: 2026-10-16. Design choices are collected in `docs/decisions/0009-backtest-simulator-design.md`. v1.1 resolves Codex's T-008 findings B1–B5 and its non-blocking notes; v1.2 resolves B6–B7 (decision 0009, re-review sections). v1.2.1 aligns §6.2 with the accepted T-008 implementation (Claude's review note N1, `BLOCKED_NAV`) and §12 with decision 0010. No behaviour change.

This document defines how the daily simulator turns market records, a schedule and an order generator into fills, cash, daily equity and metrics. It reuses the accepted signal, target and planner code unchanged (`docs/portfolio-spec.md`) and the data layer (`docs/data-spec.md`). Reference cases: `tests/fixtures/backtest_cases.json`, computed by Claude's own calculator outside the repository (§11).

**Scope of v1.x (T-008):** simulator, cost model, schedules, the strategy and baseline order generators, and per-run metrics, on **synthetic data**. **Not in scope:**
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
| `SETTLEMENT_LAG` | 2 sessions (integer ≥ 1) | Net sale proceeds become settled cash at the start of the session `SETTLEMENT_LAG` sessions after the fill session, before that session's fills |
| `DISTRIBUTION_LAG` | 20 sessions (integer ≥ 1) | Distribution cash becomes settled `DISTRIBUTION_LAG` sessions after the ex-date. A **declared synthetic assumption**, not a guarantee: the canonical record has no pay date, and a real payment may come later. Real-data runs need pay-date evidence or an owner-approved approximation with a sensitivity run (decision 0009) |
| `ANNUALISATION` | 252 | Sessions per year for metrics (same as `Params`) |

**Cost validity.** Every cost parameter is finite. `COMMISSION_RATE`, `COMMISSION_MIN`, `SLIPPAGE` and each `HALF_SPREAD` are ≥ 0, and `COST_MULTIPLIER` is > 0. For every run instrument, `COST_MULTIPLIER × (HALF_SPREAD_i + SLIPPAGE) < 1`, so every sell fill price is positive at a positive open. Otherwise `BACKTEST_COSTS`.

There is no commission maximum and no stamp duty in v1.x. Both are UNVERIFIED in the feasibility matrix and enter only by amendment. Cash earns 0% (protocol §5).

## 2. Inputs

### 2.1 Market records

- **`calendar`:** ordered exchange sessions, including the warm-up history before `start`. It must satisfy data spec §2 (strictly increasing, unique).
- **`start`, `end`:** sessions in `calendar`, with `start < end`. The backtest runs on sessions `start … end`; earlier sessions serve only as signal history.
- **Price records:** the canonical `PriceRecord` (data spec §2) gains one optional field, **`open`** (number or `None`, same `unit` as `close`, converted by the same GBX ÷ 100 rule).
  - `open` is the session's official opening price, **unadjusted**.
  - `open = None` means no open is known for that session; the record's close is still required and valid.
  - **An absent observation is the absence of a record.** No record for an instrument at a session means no open and no close there: a gap (data spec §3). A record whose `close` is `None` is an **invalid supplied price** (`DATA_INVALID_PRICE`), not a gap, and is refused at admission (§2.2).
  - Consequence: a buy can only fill at a session with a record, and every record has a valid close, so a held instrument always has a known close from its first fill onward. "Last known close" (§3 step 4) is therefore always defined.
  - Raw-dataset storage and CSV import are unchanged in v1.x: `write_raw_dataset` refuses any record with a non-`None` open (`DataStoreError("OPEN_PRICES_UNSUPPORTED", "prices")`) until a data card adds them to the raw-dataset schema (§12).
- **Distribution records** and **jump exceptions:** as in the data spec.
- **`universe`, `asset_class`, `HALF_SPREAD`:** for every instrument any generator may trade.

### 2.2 Admission (before the first session)

Admission uses only the **run's instrument set**: the strategy universe for the strategy, or the baseline's own instruments (§6.3). Records of other instruments in the bundle are ignored; for example VWRL is not part of the strategy run. It also uses only records dated **≤ `end`**: prices by `date`, distributions by `ex_date`, exceptions by `date`. Later records are ignored, never validated and never used. `run_backtest` raises `BacktestInputError(code, detail)` and simulates nothing if:

| Code | Condition |
|---|---|
| `BACKTEST_CALENDAR` | `calendar` invalid, or `start`/`end` not sessions in it, or `start ≥ end` |
| `BACKTEST_SCHEDULE` | Explicit `decision_dates` not strictly increasing, duplicated, not sessions, before `start`, or not before `end` |
| `BACKTEST_DATA_EXCLUDED` | `build_dataset` at `t = end` over the bounded inputs of §2.3 (calendar sessions ≤ `end`) reports any instrument-**excluding** code (data spec §3) for a run instrument |
| `BACKTEST_OPEN` | An `open` that is not `None` is non-finite or ≤ 0 (after unit conversion) |
| `BACKTEST_SPREAD` | A run instrument has no `HALF_SPREAD` |
| `BACKTEST_COSTS` | The cost validity rule of §1 fails |
| `BACKTEST_PARAMS` | A parameter of the wrong type or range: lags not integers ≥ 1, `INITIAL_CASH` not finite and > 0, `ANNUALISATION` not a positive integer |

Admission is **fail-closed for the whole run**: an excluding error anywhere up to `end` refuses the run, even if it lies after some decision dates. This is separate from the causal rule of §2.3 and §9.1.

Non-excluding flags are **not** admission errors:
- An unapproved `DATA_JUMP` makes `data_ok` false at the decisions it affects, giving `BLOCKED_DATA` (§6).
- `DATA_STALE` leaves `data_ok` true. A held instrument with a missing close at `d` is ineligible, so the planner returns `BLOCKED_HELD_INELIGIBLE` (portfolio spec §6.1).

### 2.3 Point-in-time inputs for each decision

Every `build_dataset` call made at a decision `d` receives:
- `calendar` sessions ≤ `d`, with `t = d`;
- the run's instrument set;
- price records with `date ≤ d` and distribution records with `ex_date ≤ d`;
- **only the exception entries with `date ≤ d`** from the frozen snapshot, in research mode with the snapshot's version. A later entry is outside the call's calendar, and must neither be seen nor reported as `DATA_INVALID_EXCEPTION` at an earlier decision.

The run records the snapshot's `exceptions_version` and the data spec §7.1 `exceptions_digest` of the **entire supplied snapshot**, the same formula over all entries. That fingerprint is identical however `end` is chosen. Each decision also records how many entries it was given.

The **exchange calendar** is the one input used beyond `d`, and only for two things: the schedule (§5, which needs the next session to know a period has ended) and session counting for lags. A published exchange calendar is known in advance; no market observation after `d` is ever used to make a decision at `d`.

## 3. The session loop

For each session `d` from `start` to `end`, in order:

1. **Settle.** Every unsettled lot whose settlement session is `d` or earlier moves to settled cash. Lags are ≥ 1, so a lot created during `d` never settles at `d`. Lots due after `end`, including beyond the supplied calendar, stay unsettled and are counted in NAV (BT10).
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

**Buy affordability.** Start from `q = min(ordered, max(0, floor(settled / f)))`. While `q > 0` and `q × f + C(q) > settled + 1e-9`, reduce `q` by 1. This is the largest affordable quantity, never negative. If `q = 0`, including whenever settled cash is ≤ 0 after an earlier `SHORTFALL` (in this session's sells or before), the buy is `SKIPPED_CASH` with quantity 0, commission 0 and no change to cash or holdings (BT12). It handles a gap-up open the planner could not see (the planner sized the order on the previous close with `BUY_BUFFER`). Buys are processed in ascending `id`, so earlier buys can use up the cash for later ones.

**Exits are never blocked.** A sell always executes when there is an open and a holding, even if the commission minimum makes its net proceeds negative. Settled cash may then go below zero; the session is flagged `settled_negative`. The planner treats negative settled cash as invalid input (`INVALID_CASH`), so the strategy records `BLOCKED_INVALID_INPUT` and places no orders until settled cash is ≥ 0 again. Baselines likewise make no buys while it is negative.

No order may exceed one session's life, partially fill for liquidity reasons, or trade fractional shares.

**Order validity.** Every order a generator returns must have:
- an instrument in the run's instrument set;
- side `BUY` or `SELL`;
- quantity an `int` (not `bool`) > 0;
- at most one order per instrument per decision.

Any violation raises `BacktestInputError("BACKTEST_ORDER", detail)` and stops the run, because a malformed order is a generator bug. These are simulator input guarantees, not approval for broker execution.

**Exits never blocked** is a **simulation assumption** for v1.x. It is not the engine's data-safety rule ("never sell because of bad data") and it gives no permission to borrow for fees. In Phase 4 the risk gate checks non-negative cash after all fees, so a `SHORTFALL` sale would be refused there. Every `SHORTFALL` stays visible in the results (§10).

## 5. Schedules

| Schedule | Decision sessions |
|---|---|
| `weekly` (strategy primary) | The last session of each ISO week (ISO year + week number) in `calendar`. A Friday holiday moves it to Thursday; the ISO week spanning New Year is one week |
| `monthly` (strategy robustness variant; all baselines) | The last session of each calendar month in `calendar` |

Explicit `decision_dates` (tests, scripted cases) must pass `BACKTEST_SCHEDULE` (§2.2).

A session counts only if the **next** session in `calendar` exists and falls in a later period. The final supplied session is never a decision session, because whether its period has ended is unknown. Only sessions in `start … end − 1` are used (§3 step 5).

## 6. Order generators

A generator is a function `(d, state, market) → orders | status`. `state` holds holdings, settled cash, unsettled cash and NAV at the close of `d`. Every decision records its `status` (`OK`, or the `BLOCKED_*` code), its orders, and for the strategy its `TargetResult` diagnostics.

### 6.1 Strategy

At decision `d`:
1. `build_dataset` with the point-in-time inputs of §2.3, giving `dates`, `tr_close`, `trade_close`, `data_ok`.
2. `compute_signals` → `compute_targets` → `plan_orders`, unchanged. `AccountState`:
   - `holdings`;
   - `cash_settled` and `cash_unsettled` from `state`;
   - `open_orders = False`, because every order has filled or been cancelled by the next close;
   - `reconciliation_clean = True`;
   - `data_ok` from step 1.
3. Prices are `trade_close` at `d`. An `InvalidInputError` is caught and recorded as `BLOCKED_INVALID_INPUT` with its code; no orders. A planner `BLOCKED_*` status is recorded; no orders.

### 6.2 Baseline rebalancer

Baselines use one simple rebalancer, **not** the strategy planner. The planner's volatility ceiling would block a 60/40 portfolio, and baselines have no ceiling. Given target weights `w`, at decision `d`:
- If NAV ≤ 0, record `BLOCKED_NAV`; no orders.
- Build with the point-in-time inputs of §2.3 over the baseline's instruments. If `data_ok` is false, record `BLOCKED_DATA`; no orders.
- `NAV` as in §3.4. Actual weights `a_i = q_i P_i / NAV`, with `P_i = trade_close` at `d`.
- Instruments with no `P_i` at `d` are **not traded**: never sold or bought for missing data.
- **The keys of `w` are the traded set.** An instrument absent from `w` is not traded at `d`, even if held; only an explicit `w_i = 0` exits (this is how the moving-average rule says "not traded").
- Trade set, among the keys of `w`: `|a_i − w_i| > BAND + TOL`, or `w_i = 0` and `q_i > 0`. Target shares `q*_i = floor(w_i × NAV / P_i + FLOOR_EPS)`.
- Settled-cash limit exactly as portfolio spec §6.3 step 5 (`BUY_BUFFER`, `COMMISSION_RESERVE` per buy, scale factor `k`, floor).
- Drop zero deltas. Sells first, then buys, each in ascending `id`.

`BAND`, `TOL`, `FLOOR_EPS`, `BUY_BUFFER` and `COMMISSION_RESERVE` are taken from `Params`.

### 6.3 Baselines (protocol §5)

All baselines use the `monthly` schedule, the same cost model and the same `INITIAL_CASH`.

| Baseline | Targets at each decision |
|---|---|
| **60/40 (deciding)** | VWRL 0.60, VGOV 0.40 |
| **Global equity (monthly band)** | VWRL 1.00. This is the protocol's "global equity buy-and-hold" made concrete: bought at the first decision, then rebalanced monthly only when the drift exceeds the band. Distributions sit as cash and are **not** reinvested immediately, only when a band breach triggers a trade |
| **10-month moving-average rule** | For each of the N strategy-universe instruments: if `tr_close` at `d` is above the mean of `tr_close` at the last 10 `monthly`-schedule sessions in `calendar` up to and including `d` (warm-up month-ends before `start` count), the target is `1/N`; otherwise 0. If any of those 10 values is missing, or fewer than 10 exist, the instrument is **not traded** at `d`. It is neither bought nor sold, even if held; this is not a zero-target exit. The 10 sessions come from the known schedule (§2.3), so the current month-end `d` is included |
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

**Undefined metrics.** Metrics are never clamped and never NaN or complex. When a metric is undefined, it is `None` and `undefined[metric]` names the reason:

| Reason | When | Metrics affected |
|---|---|---|
| `NON_POSITIVE_NAV` | Any `N_k ≤ 0`. `insolvent_on` = the first such session | All return-based metrics: `ann_return`, `ann_vol`, `sharpe`, `max_drawdown`, `max_drawdown_sessions`, `monthly_returns`, `turnover`, `cost_drag` |
| `SHORT_SERIES` | `T < 2` (fewer than two daily returns) | `ann_vol`, `sharpe` |
| `ZERO_STDEV` | The return stdev is exactly 0 | `sharpe` |

The ledger and the totals (§7) are always reported in full. A run with `NON_POSITIVE_NAV` is a valid record of an infeasible path; it is not repaired or terminated early.

These are run-level descriptions. Gate 3 uses paired monthly returns and its own statistics (protocol §6), specified in a later card.

## 9. Required properties (tests in addition to §11)

1. **No look-ahead (causal domain).** For two inputs that **both pass admission** and are identical in every record and exception entry dated ≤ `d`, every decision at sessions ≤ `d` (status, orders, diagnostics) is identical. Test it by perturbing a price, an open, a distribution and an exception entry after `d`. Changing the open at `d + 1` changes only that session's fills and later values. Future data that fails admission is a separate test (§2.2), not a leakage case.
2. **Cash identity.** At every session: `settled + unsettled = INITIAL_CASH + Σ net sale proceeds + Σ distributions − Σ buy costs`, using the recorded fills (tolerance 1e-9 × scale).
3. **NAV identity.** `NAV = settled + unsettled + Σ q × last close` at every session.
4. **Settled cash** never goes below 0 except through a `SHORTFALL` sell, and the strategy places no orders while it is negative.
5. **Determinism.** The same inputs give an identical `BacktestResult`.
6. **Shared logic.** The strategy generator calls the accepted `compute_signals`, `compute_targets` and `plan_orders`. No copy of their logic exists in the backtest package.
7. **Holdings never go negative.** No fractional shares; no order survives past its fill session.

## 10. Reporting anomalies

A backtest whose ledger ever shows `settled_negative`, `stale` valuations, blocked decisions or `NON_POSITIVE_NAV` is still a valid **record**, but those counts and reasons must be reported with any metric (§7 totals, §8). Nothing is hidden or silently repaired.

## 11. Reference cases (`tests/fixtures/backtest_cases.json`)

Produced by Claude's independent calculator; tolerance 1e-12 relative, 1e-9 absolute. Simulator cases use **scripted orders**: a test generator returns the listed orders at the listed decision dates. This isolates fills, cash and valuation from the strategy.

| Case | Exercises | Key expected result |
|---|---|---|
| BT1_buy_fill_and_valuation | Fill at the next open with spread and slippage; GBX ÷ 100; minimum commission; close valuation | SYN_A 50 @ 100.15, commission 3.00; SYN_B 100 @ £20.05; settled 2,981.50; NAV 10,041.50 then 10,071.50 |
| BT2_settlement_lag | T+2 settlement of sale proceeds | Sale at Wed open; Thu buy limited to 9 shares (`CASH_LIMITED`); Fri buy of 100 filled after settlement |
| BT3_distribution_entitlement | Ex-date entitlement at the start of the session; GBX amount; distribution lag | 40 shares × £0.50 = £20 unsettled; the 10 shares bought at the ex-date open get nothing |
| BT4_gap_up_cash_limited | Largest affordable quantity incl. commission; ascending-id buy order | SYN_A 99 → 95; SYN_B 20 → 9; SYN_C `SKIPPED_CASH`; settled 7.09759 |
| BT5_missing_open_and_absent_observation | A valid record with `open = None`; an absent observation | SYN_B order cancelled (`NO_PRICE`); SYN_A has no Wed record, so it is valued at 101 and listed stale. (`close = None` would be BV1) |
| BT6_min_commission_shortfall | A sale whose commission exceeds its proceeds | Net −2.0005; settled −1.991; `SHORTFALL`; `settled_negative` |
| BT7_cost_multiplier_2x | Every cost component doubled | Fill 100.30; commission 6.00 |
| BT9_settlement_lag_1 | `SETTLEMENT_LAG = 1` | Wed-open sale settles at Thu open and funds the Thu buy of 100 in full |
| BT10_lots_pending_at_end | Lots still pending at `end` | Sale proceeds 996.50 and distribution 10.00 unsettled at `end`; NAV 10,003.00 |
| BT11_sell_cost_stress_2x | Sell-side stress | Sell fill 99.70 at m = 2 (99.85 at m = 1): stress lowers a sell price; commission 9.8703 |
| BT12_buy_after_shortfall | Buy after a permitted negative balance | Same-session buy after a `SHORTFALL` sell, and next-session buy: both `SKIPPED_CASH`, quantity 0 |
| BT8_schedules | ISO-week and month ends with holidays and a year boundary | Weekly: 2025-12-19, 12-24, 2026-01-02, 01-09, 01-16, 01-23, 01-29; monthly: 2025-12-31, 2026-01-29; the final session is never included |
| RB1–RB4 | Baseline rebalancer | Band trades with `k` scaling (15 VWRL, 238 VGOV); unsettled cash unusable (1 VGOV); inside the band no trade; exit and no trade on a missing price |
| MT1_metrics | Metric definitions | Values in the fixture, cross-checked by a second independent computation |
| MT2–MT5 | Undefined metrics | MT2 `SHORT_SERIES`; MT3 (BT6's NAV) and MT4 (NAV hits 0) `NON_POSITIVE_NAV` with `insolvent_on`; MT5 `ZERO_STDEV` |
| BV1–BV8 | Admission and order validation codes | `BACKTEST_DATA_EXCLUDED`, `BACKTEST_COSTS`, `BACKTEST_ORDER` (×3), `BACKTEST_SCHEDULE`, `BACKTEST_PARAMS`, `BACKTEST_OPEN` |

## 12. Later cards (dependencies)

| Card | Content | Needed before |
|---|---|---|
| Data: open prices in raw datasets | Raw-dataset schema v2 with `open`; CSV column; T-007 split and reader updated; distribution **pay-date** evidence, or an owner-approved `DISTRIBUTION_LAG` approximation with a sensitivity run | Any backtest on real data |
| Gate 3 statistics | Paired monthly ΔSR, stationary block bootstrap, walk-forward windows by calendar year, simpler-rule test | Any Gate 3 result |
| Experiment registry | SQLite append-only rows (protocol §2), with code commit (clean-checkout rule), config hash, dataset ids and manifest digests | Any run on real data |
| Pre-registration | `research/hypotheses/H-001` with variants V1–V3 (decisions 0008, 0010), frozen by the owner from evidence | Any run on real data |
