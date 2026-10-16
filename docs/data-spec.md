# Data Layer Specification (v1)

Status: **Review — awaiting Codex's check (T-005).** Author: Claude. Last updated: 2026-10-16.

This document defines how raw daily price records become the inputs the portfolio engine expects (`docs/portfolio-spec.md` §2). It is source-agnostic: the data feed is still undecided (feasibility D5), so every source is read through an adapter into the canonical record format below. Reference cases: `tests/fixtures/data_cases.json`, explained in §9.

## 1. Outputs (the contract with the engine)

For a decision date t, the data layer produces:

| Output | Type | Used by |
|---|---|---|
| `dates` | Ordered list of exchange sessions ending at t | `compute_signals` |
| `tr_close` | Per instrument: one value per session in `dates`, `None` where missing | `compute_signals` |
| `trade_close` | Per instrument: the last session's unadjusted close in GBP, or `None` | `plan_orders` prices |
| `data_ok` | Boolean: true only if every check in §7 passes | `AccountState.data_ok` |
| `report` | Every error and flag found, with instrument, date and code | Owner, alerts |

All prices are in **GBP**. Nothing dated after t is ever included.

## 2. Inputs

### 2.1 Session calendar

A list of trading-session dates for the exchange (London Stock Exchange, `XLON`), supplied as a versioned file with a manifest. The data layer never invents or infers sessions; weekends and holidays are absent because the calendar omits them.

### 2.2 Canonical records (what every adapter produces)

**Price record:** `instrument`, `date`, `close` (unadjusted last close), `unit`.
**Distribution record:** `instrument`, `ex_date`, `amount` (per share), `unit`.

- `unit` comes from the **feed's metadata** for that record or instrument. It is never inferred from a fund name or a web page (feasibility D3).
- Allowed units: `GBP` and `GBX` (pence). Any other unit is an error.

## 3. Record-level validation

Each failure is recorded in the report with its code. Any error makes `data_ok` false. Errors are never repaired silently.

| Code | Condition |
|---|---|
| `DATA_UNKNOWN_UNIT` | Unit not `GBP` or `GBX` |
| `DATA_INVALID_PRICE` | Close missing, non-finite or ≤ 0 |
| `DATA_INVALID_DISTRIBUTION` | Amount non-finite or < 0 |
| `DATA_OFF_CALENDAR` | Price or distribution dated on a non-session date |
| `DATA_DUPLICATE` | Two price records for the same instrument and date, or two distributions for the same instrument and ex-date |
| `DATA_DISTRIBUTION_WITHOUT_PRICE` | A distribution whose ex-date has no valid price for that instrument |
| `DATA_FUTURE_RECORD` | Any record dated after t. It signals an adapter bug that could leak future data |

Every code above is an error. An instrument with any error code is **excluded from `tr_close` and `trade_close`** (all its values `None`). The engine then treats it as ineligible, and the planner blocks if it is held (`BLOCKED_HELD_INELIGIBLE`), so no sale is ever caused by bad data.

## 4. Unit conversion

`GBX` values (closes and distribution amounts) are divided by 100. `GBP` values are unchanged. The original unit of each instrument is recorded in the manifest. If one instrument's records arrive in mixed units, each record is converted using its own unit.

## 5. Trade close

`trade_close[i]` = the converted close at session t, or `None` if instrument i has no valid close at t. A stale last price is never carried forward.

## 6. Total-return series

For each instrument, over the sessions in `dates`, with converted prices P and distributions D (D = 0 when no ex-date falls on that session):

- At the instrument's **first** valid price session s₀: `tr[s₀] = P[s₀]`.
- At each later session s with a valid price: let p be the **previous session with a valid price**. Then

  `tr[s] = tr[p] × (P[s] + D[s]) / P[p]`

- At a session with no valid price: `tr[s] = None`. Nothing is filled. The chain resumes at the next valid price, measured from the last valid one.

This assumes distributions are reinvested at the ex-date close. Accumulating funds simply have D = 0.

## 7. Dataset checks (set `data_ok`)

The abnormal-move and stale checks run only on instruments **without** record errors; an excluded instrument is already reported.

| Check | Rule | Effect |
|---|---|---|
| Record errors | Any §3 error | `data_ok` false |
| Abnormal move | `|P[s] / P[p] − 1| > JUMP_LIMIT` between consecutive valid prices, **ignoring distributions** | Flag `DATA_JUMP`; `data_ok` false **unless** the (instrument, date) pair is listed in the approved-exceptions file |
| Stale at t | Instrument in the universe has no valid price at t | Flag `DATA_STALE`; `data_ok` stays true (the engine handles it as `missing_data`) |

`JUMP_LIMIT` = 0.25 (25% in one session). The approved-exceptions file is versioned, and every entry carries a reason and the owner's approval date. A flagged jump is a question for a person, never an automatic fix.

## 8. Storage, manifests and the holdout

- **Storage:** canonical records and built series are written as Parquet under `data/` (gitignored).
- **Manifest:** one JSON per dataset in `manifests/` (committed), with: source name and adapter version, retrieval timestamp, instrument list with original units, date range, row counts, SHA-256 of each data file, calendar manifest reference, and the code commit that built it. A dataset without a manifest cannot be used.
- **Holdout:** a split function writes the holdout period to a path the caller provides. It **refuses** (`HOLDOUT_PATH_FORBIDDEN`) any path inside the repository. The development dataset must contain no record dated in the holdout period. Holdout dates come from the charter and are not set yet.

## 9. Reference cases (`tests/fixtures/data_cases.json`)

| Case | Exercises | Key expected result |
|---|---|---|
| D1_gbx_conversion | GBX closes divided by 100 | 1000p, 1010p, 995p → £10.00, £10.10, £9.95 |
| D2_distribution | Total return with a distribution on the ex-date | P 100, 99, 101 with D = 1 on day 2 → tr 100, 100, 102.0202… |
| D3_missing_session | Gap mid-series; chain resumes from last valid | Missing day 3 → `None`; day 4 measured from day 2 |
| D4_stale_at_t | No close at t | `trade_close` `None`; `DATA_STALE` flag; `data_ok` true |
| D5_jump_flag | 40% one-day move | `DATA_JUMP`; `data_ok` false |
| D6_jump_approved | Same move listed in exceptions | No jump flag; `data_ok` true |
| D7_off_calendar | Record on a Saturday | `DATA_OFF_CALENDAR`; instrument excluded; `data_ok` false |
| D8_duplicate | Two closes for one date | `DATA_DUPLICATE`; instrument excluded |
| D9_unknown_unit | Unit `USD` | `DATA_UNKNOWN_UNIT`; instrument excluded |
| D10_distribution_without_price | Ex-date on a session with no close | `DATA_DISTRIBUTION_WITHOUT_PRICE`; instrument excluded |
| D11_future_record | Record dated after t | `DATA_FUTURE_RECORD`; instrument excluded; `data_ok` false |
| D12_gbx_distribution | GBX close and GBX distribution | Both divided by 100 before the total-return step |
| D13_mixed_units | One instrument, records in GBP and GBX | Each converted by its own unit |
| D14_holdout_path | Holdout path inside vs outside the repo | Inside (even under gitignored `data/`) → `HOLDOUT_PATH_FORBIDDEN`; outside → accepted |

## 10. Out of scope (v1)

Downloading from any provider (adapters for a real feed come after feasibility D5), FX conversion (v1 is GBP-only), corporate actions other than cash distributions (splits are an open question for the first real adapter), and intraday data.
