# Data Layer Specification (v1.1)

Status: **Review — v1.1 awaiting Codex's re-check (T-005).** Author: Claude. Last updated: 2026-10-16.

This document defines how raw daily price records become the inputs the portfolio engine expects (`docs/portfolio-spec.md` §2). It is source-agnostic: the data feed is still undecided (feasibility D5), so every source is read through an adapter into the canonical record format below. Reference cases: `tests/fixtures/data_cases.json`, explained in §9. v1.1 resolves Codex's T-005 findings (`docs/decisions/0006-data-spec-holdout-and-jump-approvals.md`).

## 1. Outputs (the contract with the engine)

For a decision date t, `build_dataset` produces:

| Output | Type | Used by |
|---|---|---|
| `dates` | Ordered list of exchange sessions in the supplied calendar, ending at t | `compute_signals` |
| `tr_close` | Per universe instrument: one value per session in `dates`, `None` where missing | `compute_signals` |
| `trade_close` | Per universe instrument: the unadjusted close at t in GBP, or `None` | `plan_orders` prices |
| `data_ok` | Boolean: true only if no §3 error and no unapproved §7 flag | `AccountState.data_ok` |
| `report` | Every error, flag and approved exception, as (code, instrument, date), sorted by instrument, date, code | Owner, alerts, audit |
| `mode`, `exceptions_version`, `exceptions_digest` | Provenance of the jump approvals used (§7.1) | Manifest, experiment registry |

All prices are in **GBP**. Nothing dated after t is ever included.

## 2. Inputs

### 2.1 Session calendar

A list of trading-session dates for the exchange (London Stock Exchange, `XLON`), supplied as a versioned file with a manifest. The data layer never invents or infers sessions. The supplied calendar defines the build window: it must cover every record passed in.

**Calendar validity** (raise `InvalidInputError("INVALID_CALENDAR")`, compute nothing): the calendar is non-empty, strictly increasing with no duplicates, and contains t.

### 2.2 Canonical records (what every adapter produces)

**Price record:** `instrument`, `date`, `close` (unadjusted last close), `unit`.
**Distribution record:** `instrument`, `ex_date`, `amount` (per share), `unit`.

- `unit` comes from the **feed's metadata** for that record or instrument. It is never inferred from a fund name or a web page (feasibility D3).
- Allowed units: `GBP` and `GBX` (pence). Any other unit is an error.

### 2.3 Jump exceptions

**Exception entry:** `instrument`, `date`, `reason`, `approved` (ISO date of the owner's approval). How they are applied depends on the mode (§7.1).

## 3. Record-level validation

Each failure is recorded in the report with its code. Errors are never repaired silently.

| Code | Condition | Effect |
|---|---|---|
| `DATA_UNKNOWN_INSTRUMENT` | Price or distribution for an instrument not in the universe | Reported; `data_ok` false (likely an adapter mapping bug) |
| `DATA_FUTURE_RECORD` | Any record dated after t. It signals an adapter bug that could leak future data | Instrument excluded |
| `DATA_OFF_CALENDAR` | Record dated on a date **not in the supplied calendar**, including any date before its first session | Instrument excluded |
| `DATA_UNKNOWN_UNIT` | Unit not `GBP` or `GBX` | Instrument excluded |
| `DATA_INVALID_PRICE` | Close missing, non-finite or ≤ 0 | Instrument excluded |
| `DATA_INVALID_DISTRIBUTION` | Amount non-finite or < 0 | Instrument excluded |
| `DATA_DUPLICATE` | Two price records for one instrument and date, or two distributions for one instrument and ex-date | Instrument excluded |
| `DATA_DISTRIBUTION_WITHOUT_PRICE` | A distribution whose ex-date has no valid price for that instrument | Instrument excluded |
| `DATA_INVALID_EXCEPTION` | A jump exception with an instrument not in the universe, a date not in the calendar, an empty or blank reason, or an approval that is not a valid ISO date (YYYY-MM-DD) | Entry ignored; reported; `data_ok` false |

Checks run in the table's order for each record; a record that fails one is not checked further.

**Excluded** means all of the instrument's `tr_close` and `trade_close` values are `None`.

**Any error sets `data_ok` false.** In the accepted engine, the planner checks `data_ok` before holdings (portfolio spec §6.1, check 4), so **the whole run returns `BLOCKED_DATA`**, whether or not the bad instrument is held. No order is placed, and no sale is ever caused by bad data. A stale instrument (§7) is not an error: `data_ok` stays true, the engine marks it `missing_data`, and the planner returns `BLOCKED_HELD_INELIGIBLE` only if it is held.

## 4. Unit conversion

`GBX` values (closes and distribution amounts) are divided by 100. `GBP` values are unchanged. Each record is converted using its own unit, so mixed units for one instrument are handled. The original unit of each instrument is recorded in the manifest.

## 5. Trade close

`trade_close[i]` = the converted close at session t, or `None` if instrument i has no valid close at t. A stale last price is never carried forward.

## 6. Total-return series

For each instrument, over the sessions in `dates`, with converted prices P and distributions D (D = 0 when no ex-date falls on that session):

- At the instrument's **first** valid price session s₀: `tr[s₀] = P[s₀]`.
- At each later session s with a valid price: let p be the **previous session with a valid price**. Then

  `tr[s] = tr[p] × (P[s] + D[s]) / P[p]`

- At a session with no valid price: `tr[s] = None`. Nothing is filled. The chain resumes at the next valid price, measured from the last valid one.

This assumes distributions are reinvested at the ex-date close. Accumulating funds simply have D = 0.

## 7. Dataset checks

The abnormal-move and stale checks run only on instruments **without** record errors.

| Check | Rule | Effect |
|---|---|---|
| Abnormal move | `|P[s] / P[p] − 1| > JUMP_LIMIT`, where p is the previous valid-price session, **ignoring distributions**. p may be several sessions earlier if there are gaps, so this is a move between consecutive *valid prices*, not necessarily a one-session move | Flag `DATA_JUMP`; `data_ok` false, **unless** an exception in effect (§7.1) covers (instrument, s). Then report `DATA_JUMP_APPROVED` instead, and `data_ok` is unaffected |
| Stale at t | Universe instrument with no valid price at t | Flag `DATA_STALE`; `data_ok` stays true |

`JUMP_LIMIT` = 0.25. A flagged jump is a question for a person, never an automatic fix.

### 7.1 Which exceptions are in effect: two modes

The builder takes `mode` = `operational` or `research`.

| | **Operational** (paper and live runs) | **Research** (backtests and evaluation) |
|---|---|---|
| Purpose | Decide today's trades with only information available at t | Clean known data errors in history, consistently across a whole evaluation |
| An exception is in effect if | Valid (§3) **and** `approved ≤ t` | Valid (§3), regardless of approval date |
| Exceptions source | The current exceptions file | A frozen, versioned snapshot: `manifests/exceptions/<version>.json`, committed |
| `exceptions_version` | Optional | **Required**; missing → `InvalidInputError("INVALID_EXCEPTIONS_VERSION")` |

**Why two modes.** In operational mode, an approval made after t was not information available at t, so it cannot change a past decision. In research mode, cleaning uses later knowledge by design. That is allowed **only** as a pinned snapshot that is fixed before the evaluation: the snapshot used by a pre-registered hypothesis must be committed before that hypothesis's first registered run. The snapshot is cleaning, not information at t, and it is recorded as such.

**Provenance.** `exceptions_digest` = SHA-256 (hex) of the UTF-8 bytes of `json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Here `entries` is the list of supplied exception entries, each reduced to the four keys of §2.3, sorted by (instrument, date). The digest covers every supplied entry, valid or not. The dataset manifest and every experiment-registry entry record `mode`, `exceptions_version` and `exceptions_digest`.

## 8. Storage, manifests and the holdout

### 8.1 Storage and manifests

- **Storage:** canonical records and built series are written as Parquet under `data/` (gitignored).
- **Manifest:** one JSON per dataset in `manifests/` (committed), with: source name and adapter version, retrieval timestamp, instrument list with original units, date range, row counts, SHA-256 of each data file, calendar manifest reference, exceptions provenance (§7.1), and the code commit that built it. A dataset without a manifest cannot be used.

### 8.2 Holdout containment guard

`check_holdout_path(path, repo_root, agent_workspaces)` refuses (`HOLDOUT_PATH_FORBIDDEN`) any path equal to or inside the repository root **or any agent workspace root**. Paths are resolved, including symlinks, before comparison. A sibling whose name merely starts with a root's name is not inside it.

This is a **containment check only**. Passing it does not authorise anyone to create, read or move holdout data.

### 8.3 Holdout isolation boundary (owner-run)

The guard alone cannot keep holdout data away from agents, so these rules apply before any real data is ingested:

1. **No real data is ingested into any agent-accessible location until the charter fixes the holdout dates.**
2. **Any import that could include holdout-period dates is run by the owner, on the owner's machine, outside every agent workspace.** That includes any full-history download. The raw import is stored only in an owner location that passes the §8.2 guard.
3. **The owner runs the split there.** It writes the development dataset, containing only sessions before the holdout start, and that is the only dataset copied into an agent-accessible location. The holdout portion stays in the owner location.
4. **Agent-run adapters** (T-007 onward) must take an end date and refuse any request reaching the holdout start or later. Until holdout dates exist, agent-run adapters may only be used with synthetic data.
5. The one-time holdout evaluation is run by the owner (research protocol §3).

## 9. Reference cases (`tests/fixtures/data_cases.json`)

| Case | Exercises | Key expected result |
|---|---|---|
| D1_gbx_conversion | GBX closes divided by 100 | 1000p, 1010p, 995p → £10.00, £10.10, £9.95 |
| D2_distribution | Total return with a distribution on the ex-date | P 100, 99, 101 with D = 1 on day 2 → tr 100, 100, 102.0202… |
| D3_missing_session | Gap mid-series; chain resumes from last valid | Missing day 3 → `None`; day 4 measured from day 2 |
| D4_stale_at_t | No close at t | `trade_close` `None`; `DATA_STALE`; `data_ok` true |
| D5_jump_flag | 40% move, no exception | `DATA_JUMP`; `data_ok` false |
| D6_jump_approved_research | Research mode, snapshot pinned, approval after t | `DATA_JUMP_APPROVED`; `data_ok` true |
| D6b_operational_future_approval | Operational mode, approval after t | Not in effect: `DATA_JUMP`; `data_ok` false |
| D6c_operational_approval_by_t | Operational mode, approval on or before t | `DATA_JUMP_APPROVED`; `data_ok` true |
| D6d_exception_empty_reason | Empty reason | `DATA_INVALID_EXCEPTION` + `DATA_JUMP`; `data_ok` false |
| D6e_exception_bad_date | Malformed approval date | `DATA_INVALID_EXCEPTION` + `DATA_JUMP`; `data_ok` false |
| D7_off_calendar | Record on a Saturday before the window | `DATA_OFF_CALENDAR`; instrument excluded |
| D8_duplicate | Two closes for one date | `DATA_DUPLICATE`; instrument excluded |
| D9_unknown_unit | Unit `USD` | `DATA_UNKNOWN_UNIT`; instrument excluded |
| D10_distribution_without_price | Ex-date on a session with no close | `DATA_DISTRIBUTION_WITHOUT_PRICE`; instrument excluded |
| D11_future_record | Record dated after t | `DATA_FUTURE_RECORD`; instrument excluded |
| D12_gbx_distribution | GBX close and GBX distribution | Both divided by 100 before the total-return step |
| D13_mixed_units | One instrument, GBP and GBX records | Each converted by its own unit |
| D14_holdout_path | Repo and agent-workspace roots | Inside either (including a repo sibling inside the workspace) → forbidden; `/srv/...` and `/work2/...` accepted |
| D15_gap_jump | 100, missing, 130 | `DATA_JUMP` on the 130 session |
| D16_before_calendar | Real session before the supplied calendar | `DATA_OFF_CALENDAR`; instrument excluded |
| D17_unknown_instrument | Record for an id outside the universe | `DATA_UNKNOWN_INSTRUMENT`; `data_ok` false; others unaffected |
| DV1–DV4 | Empty, duplicate, unsorted calendar; t not a session | `INVALID_CALENDAR` |
| DV5 | Research mode without a version | `INVALID_EXCEPTIONS_VERSION` |

Every case also gives the expected `exceptions_digest`.

## 10. Out of scope (v1), and where each is gated

| Item | Gate |
|---|---|
| Downloading from any provider | T-007, after feasibility D5 and the holdout dates (§8.3) |
| Share splits and other non-cash corporate actions | T-007 must define them before any real adapter's output is used |
| Distributions declared in a currency other than GBP or GBX | T-007 must handle or reject them; v1 rejects unknown units |
| Next-session open prices for fills | T-008 (backtester) must source them before any backtest result is used |
| FX conversion, intraday data | Not in v1 |
