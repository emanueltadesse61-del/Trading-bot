# Portfolio Specification (v1.3)

Status: **Review — v1.2 awaiting Codex re-check (T-002).** Author: Claude. Last updated: 2026-10-16.

v1.1 resolves Codex's T-002 findings B1–B3, N1 and N2 (`docs/decisions/0002-t002-review-resolutions.md`). v1.2 resolves B5, the numerical handling of portfolio volatility (`docs/decisions/0003-portfolio-volatility-numerics.md`). v1.3 makes input coverage and covariance labels explicit, from Codex's T-003 review (`docs/decisions/0005-input-coverage-and-covariance-labels.md`). No rule, parameter or fixture value changed.

This document is the single authoritative definition of how target weights and orders are computed. Code that disagrees with it is wrong, or this document needs an amendment recorded in `docs/decisions/`. Reference cases live in `tests/fixtures/portfolio_cases.json` and are explained in `docs/portfolio-reference-cases.md`.

## 1. Parameters

All values are fixed in the charter before any backtest. Changing one is a new registered variant.

| Name | Value | Meaning |
|---|---|---|
| `ANNUALISATION` | 252 | Trading days per year |
| `TREND_LOOKBACKS` | 63, 126, 252 | Session lookbacks for the trend score (≈3, 6, 12 months) |
| `MOM_LONG` | 252 | Momentum lookback start |
| `MOM_SKIP` | 21 | Most recent sessions excluded from momentum |
| `VOL_WINDOW` | 60 | Daily returns used for per-asset volatility |
| `COV_WINDOW` | 252 | Daily returns used for the covariance matrix |
| `TOP_N` | 4 | Momentum selection size |
| `SLEEVE_TREND`, `SLEEVE_MOM` | 0.5, 0.5 | Capital weights of the two sleeves |
| `ASSET_CAP` | 0.25 | Max weight of one risk instrument |
| `CLASS_CAP` | 0.60 | Max combined weight of one asset class |
| `VOL_CEILING` | 0.10 | Max estimated annualised portfolio volatility |
| `BAND` | 0.02 | Rebalance band, absolute weight |
| `MIN_VOL` | 0.005 | Annualised volatility below this makes an instrument ineligible |
| `BUY_BUFFER` | 0.005 | Price buffer when checking buys against settled cash |
| `COMMISSION_RESERVE` | 3.00 (GBP per buy order) | Cash reserved per buy order for commission. Provisional until T-004 confirms the real schedule |
| `TOL` | 1e-9 | Tolerance for all weight comparisons |
| `FLOOR_EPS` | 1e-9 | Added before flooring share counts, to absorb float error |
| `SYM_TOL` | 1e-12 | Max absolute asymmetry allowed in a covariance matrix |
| `PSD_TOL` | 1e-12 | Smallest eigenvalue allowed is −`PSD_TOL` |

## 2. Inputs and conventions

- **Instruments.** Each has an `id` (string), an `asset_class` in `{equity, bond, real_asset}`, and a quote currency. **v1 accepts only GBP-quoted instruments**; a non-GBP instrument is excluded from the universe at configuration time. There is no FX conversion in v1.
- **Two price series per instrument.** `tr_close`: total-return (distribution-adjusted) close, used for all returns, signals, volatility and covariance. `trade_close`: the unadjusted last close, used for valuation and order sizing. In synthetic tests they may be equal.
- **Session calendar.** The signal function receives `dates`, the exchange's ordered list of trading sessions ending at the decision date, and for every instrument exactly **one value per session** in that list, with a missing marker (NaN or null) where no valid close exists for that session. Building this from dated records against the official calendar is the data layer's job (T-005+). The signal function **never aligns, shifts or re-indexes** series; a series whose length differs from `dates` is invalid (§2.1).
- **Decision date `t`** = the last element of `dates`: the last completed session before the weekly rebalance. Nothing dated after `t` is passed in.
- **Daily return.** `r = tr_close[session] / tr_close[previous session] − 1`, simple returns over consecutive sessions in `dates`.
- **`sign(x)`** = +1 if x > 0, −1 if x < 0, 0 if x == 0.
- **Ordering.** Wherever instruments are listed or tie-broken, use ascending `id` in byte order.

### 2.1 Input validity

Inputs that break these rules are not market states; they are bugs or upstream data failures. The responsible function raises `InvalidInputError(code)` and computes nothing. The scheduled run catches it, records it, raises an alert and places no orders (`BLOCKED_INVALID_INPUT`).

| Stage | Rule | Code |
|---|---|---|
| Signals | `dates` strictly increasing with no duplicates | `INVALID_CALENDAR` |
| Signals | Every series has exactly `len(dates)` values | `INVALID_CALENDAR` |
| Signals | Every present value is finite and > 0 | `INVALID_PRICE_SERIES` |
| Targets | Every **eligible** id has an `asset_class`, and every `asset_class` is in the allowed set | `INVALID_ASSET_CLASS` |
| Targets | Every eligible id has a σ; every σ is finite and ≥ 0 (NaN is invalid; 0 is valid and fails `MIN_VOL`) | `INVALID_SIGMA` |
| Targets | Every eligible id has a trend score and a momentum return; every one is finite | `INVALID_SIGNAL` |
| Targets | Covariance is square with **unique** labels equal to the eligible ids, numeric, finite, symmetric within `SYM_TOL`, smallest eigenvalue ≥ −`PSD_TOL` | `INVALID_COVARIANCE` |
| Planner | Every holding is an integer ≥ 0 | `INVALID_HOLDING` |
| Planner | `cash_settled` and `cash_unsettled` are finite and ≥ 0 | `INVALID_CASH` |
| Planner | Every instrument held or with a positive target has a finite price > 0 | `INVALID_PRICE` |
| Planner | The covariance passes the Targets covariance rules (labels unique, numeric, finite, symmetric, PSD within tolerance) and covers every instrument held or with a positive target | `INVALID_COVARIANCE` |

A missing input is never treated as a zero: an eligible id without its asset class, σ or scores raises rather than silently receiving no weight.

Legitimate account states that cannot be traded are **statuses**, not errors (§6).

### 2.2 Portfolio volatility

Every portfolio volatility in this spec (§5 step 6, §6.3 steps 3 and 6) is computed with one function:

```text
σ(x) = sqrt(max(0, q))   where q = xᵀ Σ x
if q < −PSD_TOL:  raise InvalidInputError("INVALID_COVARIANCE")
```

Why this is safe: validation (§2.1) guarantees every eigenvalue of Σ is ≥ −`PSD_TOL`, so q ≥ −`PSD_TOL` × ‖x‖². Every weight vector here is non-negative and sums to at most 1, because there is no leverage and cash is ≥ 0, so ‖x‖² ≤ 1 and q ≥ −`PSD_TOL`. A q between −`PSD_TOL` and 0 is rounding noise and is treated as 0. A q below −`PSD_TOL` cannot come from validated inputs, so it is raised as an error, never clamped away silently.

## 3. Eligibility (per instrument, at date t)

An instrument is **eligible** only if all hold:

1. It has a valid `tr_close` for **each** of the last 253 sessions in `dates`, the last being `t` (giving 252 returns).
2. Its volatility σ (§4) is ≥ `MIN_VOL`.
3. It is GBP-quoted and on the configured universe list.

Reason codes, checked in this order:

- `insufficient_history`: every missing value in the 253-session window comes before the instrument's first valid value (it is too young), or `dates` has fewer than 253 sessions.
- `missing_data`: any missing value after its first valid value in the window, **including a missing close at t**. A stale last price is never treated as current.
- `min_vol`: rule 2 fails.

Ineligible instruments get a target weight of 0 and are excluded from every denominator, ranking and covariance matrix. `U` denotes the set of eligible instruments.

## 4. Signals (eligible instruments only)

- **Trend score.** For each lookback L in `TREND_LOOKBACKS`: `R_L = tr_close[t] / tr_close[t−L] − 1`, with t−L counted in sessions. Then `s = max(0, mean(sign(R_63), sign(R_126), sign(R_252)))`. Possible values: 0, 1/3, 2/3, 1.
- **Momentum return.** `M = tr_close[t−MOM_SKIP] / tr_close[t−MOM_LONG] − 1`.
- **Momentum selection.** Rank `U` by `M` descending; ties by ascending `id`. `TopN` = the first `min(TOP_N, |U|)` instruments. Momentum score `m = 1` if the instrument is in `TopN` **and** `M > 0`; otherwise `m = 0`.
- **Volatility.** `σ = stdev(last VOL_WINDOW daily returns, ddof=1) × sqrt(ANNUALISATION)`.
- **Covariance.** `Σ = sample covariance (ddof=1) of the last COV_WINDOW daily returns of U × ANNUALISATION`.

## 5. Target weights

Inputs are validated first (§2.1). Steps then run in this exact order.

1. **Trend sleeve.** `wT_i = (s_i / σ_i) / Σ_{j∈U} (1/σ_j)`.
2. **Momentum sleeve.** `wM_i = (m_i / σ_i) / Σ_{j∈TopN} (1/σ_j)` for `i ∈ TopN`; 0 otherwise. A TopN instrument with `M ≤ 0` keeps its place in the denominator, so its share stays in cash.
3. **Combine.** `w_i = SLEEVE_TREND × wT_i + SLEEVE_MOM × wM_i`.
4. **Asset cap.** `w_i = min(w_i, ASSET_CAP)`.
5. **Class cap.** For each class c with `W_c = Σ_{i∈c} w_i > CLASS_CAP`: multiply every `w_i` in c by `CLASS_CAP / W_c` (proportional reduction).
6. **Volatility ceiling.** `σ_p = σ(w)` (§2.2). If `σ_p > VOL_CEILING`, multiply every `w_i` by `VOL_CEILING / σ_p`. Weights are never scaled up. If `σ_p = 0`, no scaling.
7. **Cash.** `w_cash = 1 − Σ w_i`. Cash is GBP held at the broker. It is not an instrument and is exempt from both caps; it has zero volatility and zero covariance in every risk estimate.

Steps 5 and 6 only shrink weights, so earlier caps still hold. If `U` is empty, every target is 0 and `w_cash = 1`; what happens to holdings is decided by the planner (§6).

Diagnostics to record per run: `wT`, `wM`, `TopN`, weights after steps 3, 4, 5 and 6, `σ_p` before scaling, and the scale factor.

## 6. Order planning

### 6.1 Checks before any calculation, in this order

| # | Check | Outcome if it fails |
|---|---|---|
| 1 | Holdings and cash valid (§2.1) | `InvalidInputError` (`INVALID_HOLDING`, `INVALID_CASH`) |
| 2 | No open or unknown-state orders | `BLOCKED_OPEN_ORDERS` |
| 3 | Last broker reconciliation clean | `BLOCKED_RECONCILIATION` |
| 4 | Data checks passed | `BLOCKED_DATA` |
| 5 | Every held instrument (`q_i > 0`) is in the configured universe | `BLOCKED_UNKNOWN_HOLDING` |
| 6 | Every held instrument is eligible (§3) | `BLOCKED_HELD_INELIGIBLE` |
| 7 | Prices valid for every instrument held or with a positive target (§2.1) | `InvalidInputError` (`INVALID_PRICE`) |
| 8 | NAV > 0 | `BLOCKED_NAV` |
| 9 | Covariance valid and covering every instrument held or targeted (§2.1) | `InvalidInputError` (`INVALID_COVARIANCE`) |

A `BLOCKED_*` status returns no orders and raises an alert. The first failing check decides the status.

**Held instruments are never sold because they are ineligible.** Ineligibility means the data can't be trusted, and a sale decided on untrusted data is worse than waiting. Removing an instrument from the universe on purpose is an owner action: the owner sells it first, then changes the configuration. By contrast, an instrument that is **eligible with a zero target** (for example, its trend has turned negative) exits normally through the `exit` reason.

### 6.2 Inputs

Target weights `w` (§5), the eligible set `U`, current share holdings `q_i`, `trade_close` prices `P_i`, `cash_settled`, `cash_unsettled` (sale proceeds not yet settled), Σ and asset classes.

### 6.3 Steps

1. **NAV** = `cash_settled + cash_unsettled + Σ q_i P_i`.
2. **Actual weights** `a_i = q_i P_i / NAV` for every instrument held or with a positive target.
3. **Trade set S.** Instrument i is in S if any applies (record every reason that applies):
   - `band`: `|a_i − w_i| > BAND + TOL`.
   - `exit`: `w_i == 0` and `q_i > 0`.
   - `asset_cap`: `a_i > ASSET_CAP + TOL`.
   - `class_cap`: `a_i > w_i + TOL` and the actual weight of i's class `> CLASS_CAP + TOL`.
   - `vol`: `a_i > w_i + TOL` and `σ(a) > VOL_CEILING + TOL` (§2.2).
4. **Target shares** for i in S: `q*_i = floor(w_i × NAV / P_i + FLOOR_EPS)`. `Δ_i = q*_i − q_i`. Instruments not in S keep `Δ_i = 0`.
5. **Settled-cash limit.** Let `gross = Σ_{Δ_i>0} Δ_i × P_i × (1 + BUY_BUFFER)`, `n_b` = the number of buys, and `need = gross + COMMISSION_RESERVE × n_b`. If `need > cash_settled`: `k = max(0, cash_settled − COMMISSION_RESERVE × n_b) / gross`, and every buy becomes `Δ_i = floor(k × Δ_i + FLOOR_EPS)`. Sale proceeds from this run are **not** used for this run's buys.
6. **Post-trade check.** With `q' = q + Δ` and `NAV' = NAV` (costs ignored for the check), compute `a'`. Violations, and the instruments each one adds to S:
   - `a'_i > ASSET_CAP + TOL` → i (reason `repair_asset`).
   - A class's weight `> CLASS_CAP + TOL` → every i in that class with `a'_i > w_i + TOL` (reason `repair_class`).
   - `σ(a') > VOL_CEILING + TOL` → every i with `|a'_i − w_i| > TOL`, in either direction (reason `repair_vol`). An under-held hedge can push volatility up, so moving only over-weight positions is not enough.
7. **Resolution.**
   - No violations → go to step 8.
   - Violations, and step 6 added at least one instrument **not already in S** → add them and repeat steps 4–6 **once**.
   - Violations remaining after that repeat, or violations with **nothing new to add** → `BLOCKED_CONSTRAINTS`, alert, no orders.
8. **Orders.** Drop `Δ_i = 0`. Sells first, then buys, each group in ascending `id`. Each order records `id`, side, quantity, reference price `P_i`, and every reason.

### 6.4 Scope of the planner

The plan is a **reference-price approximation**. It uses the last close and a flat commission reserve. It is not approval to execute. Before any order is sent (Phase 4), the risk gate re-checks each order against fresh prices, the real commission schedule and live account cash, and rejects anything that would breach a cap or overdraw settled cash.

The planner never:

- Uses unsettled cash for buys.
- Trades fractional shares.
- Scales a weight up to reach the volatility ceiling.
- Sells because data is missing, stale or ineligible.

## 7. Failure behaviour summary

| Condition | Result |
|---|---|
| Invalid input (§2.1) | `InvalidInputError`; the run records `BLOCKED_INVALID_INPUT`, alerts, places no orders |
| Open or unknown orders | `BLOCKED_OPEN_ORDERS` |
| Reconciliation not clean | `BLOCKED_RECONCILIATION` |
| Data check failure | `BLOCKED_DATA` |
| Holding outside the configured universe | `BLOCKED_UNKNOWN_HOLDING` |
| Any held instrument ineligible (including an empty eligible set while anything is held) | `BLOCKED_HELD_INELIGIBLE` |
| Empty eligible set, nothing held | `OK`, 100% cash, no orders |
| Eligible instruments, all targets 0 | `OK`; holdings exit via `exit` |
| NAV ≤ 0 | `BLOCKED_NAV` |
| Constraints still violated, or nothing new to repair | `BLOCKED_CONSTRAINTS` |
| Buys plus commission reserve exceed settled cash | Buys scaled by k, then floored |
