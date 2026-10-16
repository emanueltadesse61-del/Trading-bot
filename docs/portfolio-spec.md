# Portfolio Specification (v1)

Status: **Review — awaiting Codex acceptance (T-002).** Author: Claude. Last updated: 2026-10-16.

This document is the single authoritative definition of how target weights and orders are computed. Code that disagrees with it is wrong, or this document needs an amendment recorded in `docs/decisions/`. Reference cases live in `tests/fixtures/portfolio_cases.json` and are explained in `docs/portfolio-reference-cases.md`.

## 1. Parameters

All values are fixed in the charter before any backtest. Changing one is a new registered variant.

| Name | Value | Meaning |
|---|---|---|
| `ANNUALISATION` | 252 | Trading days per year |
| `TREND_LOOKBACKS` | 63, 126, 252 | Trading-day lookbacks for the trend score (≈3, 6, 12 months) |
| `MOM_LONG` | 252 | Momentum lookback start |
| `MOM_SKIP` | 21 | Most recent days excluded from momentum |
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
| `TOL` | 1e-9 | Tolerance for all weight comparisons |
| `FLOOR_EPS` | 1e-9 | Added before flooring share counts, to absorb float error |

## 2. Inputs and conventions

- **Instruments.** Each has an `id` (string), an `asset_class` in `{equity, bond, real_asset}`, and a quote currency. **v1 accepts only GBP-quoted instruments**; a non-GBP instrument is excluded from the universe at configuration time. There is no FX conversion in v1.
- **Two price series per instrument.** `tr_close`: total-return (distribution-adjusted) close, used for all returns, signals, volatility and covariance. `trade_close`: the unadjusted last close, used for valuation and order sizing. In synthetic tests they may be equal.
- **Decision date `t`.** The last completed trading session before the weekly rebalance. Only data dated ≤ `t` may be read.
- **Daily return.** `r[t] = tr_close[t] / tr_close[t-1] - 1` (simple returns, consecutive valid sessions).
- **`sign(x)`** = +1 if x > 0, −1 if x < 0, 0 if x == 0.
- **Ordering.** Wherever instruments are listed or tie-broken, use ascending `id` in byte order.

## 3. Eligibility (per instrument, at date t)

An instrument is **eligible** only if all hold:

1. At least 253 consecutive valid `tr_close` values ending at `t` (giving 252 returns), with no missing value in that window.
2. Its volatility σ (§4) is ≥ `MIN_VOL`.
3. It is GBP-quoted and on the configured universe list.

Reason codes: if every missing value in the 253-row window comes before the instrument's first valid value (it is too young), the reason is `insufficient_history`; any missing value after its first valid value is `missing_data`; failing rule 2 is `min_vol`. Price arrays of different lengths are aligned on their **last** element (date t) and padded with missing values at the start.

Ineligible instruments get a target weight of 0 and are excluded from every denominator, ranking and covariance matrix. `U` denotes the set of eligible instruments.

**If a currently held instrument is ineligible, planning is blocked** (`BLOCKED_HELD_INELIGIBLE`) and an alert is raised. The system never sells because of a data problem.

## 4. Signals (eligible instruments only)

- **Trend score.** For each lookback L in `TREND_LOOKBACKS`: `R_L = tr_close[t] / tr_close[t-L] - 1`. Then `s = max(0, mean(sign(R_63), sign(R_126), sign(R_252)))`. Possible values: 0, 1/3, 2/3, 1.
- **Momentum return.** `M = tr_close[t-MOM_SKIP] / tr_close[t-MOM_LONG] - 1`.
- **Momentum selection.** Rank `U` by `M` descending; ties by ascending `id`. `TopN` = the first `min(TOP_N, |U|)` instruments. Momentum score `m = 1` if the instrument is in `TopN` **and** `M > 0`; otherwise `m = 0`.
- **Volatility.** `σ = stdev(last VOL_WINDOW daily returns, ddof=1) × sqrt(ANNUALISATION)`.
- **Covariance.** `Σ = sample covariance (ddof=1) of the last COV_WINDOW daily returns of U × ANNUALISATION`.

## 5. Target weights

Steps run in this exact order.

1. **Trend sleeve.** `wT_i = (s_i / σ_i) / Σ_{j∈U} (1/σ_j)`.
2. **Momentum sleeve.** `wM_i = (m_i / σ_i) / Σ_{j∈TopN} (1/σ_j)` for `i ∈ TopN`; 0 otherwise. A TopN instrument with `M ≤ 0` keeps its place in the denominator, so its share stays in cash.
3. **Combine.** `w_i = SLEEVE_TREND × wT_i + SLEEVE_MOM × wM_i`.
4. **Asset cap.** `w_i = min(w_i, ASSET_CAP)`.
5. **Class cap.** For each class c with `W_c = Σ_{i∈c} w_i > CLASS_CAP`: multiply every `w_i` in c by `CLASS_CAP / W_c`.
6. **Volatility ceiling.** `σ_p = sqrt(wᵀ Σ w)`. If `σ_p > VOL_CEILING`, multiply every `w_i` by `VOL_CEILING / σ_p`. Weights are never scaled up.
7. **Cash.** `w_cash = 1 − Σ w_i`. Cash is GBP held at the broker. It is not an instrument and is exempt from both caps; it has zero volatility and zero covariance in every risk estimate.

Steps 5 and 6 only shrink weights, so earlier caps still hold. If |U| = 0, all weight is cash.

Diagnostics to record per run: `wT`, `wM`, `TopN`, weights after steps 3, 4, 5 and 6, `σ_p` before and after scaling, and the scale factor.

## 6. Order planning

### Preconditions (else `BLOCKED`, alert, no orders)

- No open or unknown-state orders (`BLOCKED_OPEN_ORDERS`).
- Last reconciliation with the broker was clean (`BLOCKED_RECONCILIATION`).
- Data checks passed (`BLOCKED_DATA`).
- No held instrument is ineligible (`BLOCKED_HELD_INELIGIBLE`).

### Inputs

Target weights `w` (§5), current share holdings `q_i` (integers), `trade_close` prices `P_i`, `cash_settled`, `cash_unsettled` (sale proceeds not yet settled), Σ and asset classes.

### Steps

1. **NAV** = `cash_settled + cash_unsettled + Σ q_i P_i`.
2. **Actual weights** `a_i = q_i P_i / NAV` for every instrument with a holding or a target.
3. **Trade set S.** Instrument i is in S if any applies (record every reason that applies):
   - `band`: `|a_i − w_i| > BAND + TOL`.
   - `exit`: `w_i == 0` and `q_i > 0`.
   - `asset_cap`: `a_i > ASSET_CAP + TOL`.
   - `class_cap`: `a_i > w_i + TOL` and the actual weight of i's class `> CLASS_CAP + TOL`.
   - `vol`: `a_i > w_i + TOL` and `sqrt(aᵀ Σ a) > VOL_CEILING + TOL`.
4. **Target shares** for i in S: `q*_i = floor(w_i × NAV / P_i + FLOOR_EPS)`. `Δ_i = q*_i − q_i`. Instruments not in S keep `Δ_i = 0`.
5. **Settled-cash limit.** `need = Σ_{Δ_i>0} Δ_i × P_i × (1 + BUY_BUFFER)`. If `need > cash_settled`: `k = cash_settled / need` and every buy becomes `Δ_i = floor(k × Δ_i + FLOOR_EPS)`. Sale proceeds from this run are **not** used for this run's buys.
6. **Post-trade check.** With `q' = q + Δ`, `cash' = cash_settled + cash_unsettled − Σ Δ_i P_i`, `NAV' = NAV` (costs ignored for the check), compute `a'`. Violations:
   - `a'_i > ASSET_CAP + TOL` → add i to S (reason `repair_asset`).
   - class actual weight `> CLASS_CAP + TOL` → add every i in that class with `a'_i > w_i + TOL` (reason `repair_class`).
   - `sqrt(a'ᵀ Σ a') > VOL_CEILING + TOL` → add every i with `a'_i > w_i + TOL` (reason `repair_vol`).
7. If step 6 added anything, repeat steps 4–6 **once**. If violations remain, the plan is `BLOCKED_CONSTRAINTS` with an alert and no orders.
8. **Orders.** Drop `Δ_i = 0`. Sells first, then buys, each group in ascending `id`. Each order records `id`, side, quantity, reference price `P_i`, and reasons.

### What the planner never does

- Use unsettled cash for buys.
- Trade fractional shares.
- Scale a weight up to reach the volatility ceiling.
- Sell because data is missing or stale.

## 7. Failure behaviour summary

| Condition | Result |
|---|---|
| No eligible instruments | 100% cash target; existing holdings exit via `exit` |
| Held instrument ineligible | `BLOCKED_HELD_INELIGIBLE` |
| Open or unknown orders | `BLOCKED_OPEN_ORDERS` |
| Reconciliation not clean | `BLOCKED_RECONCILIATION` |
| Data check failure | `BLOCKED_DATA` |
| Constraints still violated after one repair | `BLOCKED_CONSTRAINTS` |
| Buy exceeds settled cash | Buys scaled down by k, then floored |
