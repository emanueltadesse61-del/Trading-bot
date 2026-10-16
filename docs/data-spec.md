# Data Layer Specification (v1.2.1)

Status: **v1.2.1 in review (T-007 requirements); §1–6 and §9 accepted in v1.1.1; §7.1 has a one-sentence provenance correction.** Author: Claude. Last updated: 2026-10-16.

This document defines how raw daily price records become the inputs the portfolio engine expects (`docs/portfolio-spec.md` §2). It is source-agnostic: the data feed is still undecided (feasibility D5), so every source is read through an adapter into the canonical record format below. Reference cases: `tests/fixtures/data_cases.json`, explained in §9. v1.1 resolves Codex's T-005 findings (`docs/decisions/0006-data-spec-holdout-and-jump-approvals.md`). v1.1.1 clarifies duplicate counting (Claude's T-006 review, note N1). v1.2 (§8, §10) adds raw-dataset storage, owner-run isolation details, declarations and a corrected corporate-action rule, from Codex's T-007 review (`docs/decisions/0007-raw-datasets-isolation-and-corporate-actions.md`); v1.2.1 resolves Codex's T-007 re-review (B4 attestation dates, B5 per-dataset publication, identity covers partition and holdout start, §7.1 provenance sentence; same decision record). The builder's behaviour and the fixture are unchanged.

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
| `DATA_DUPLICATE` | Two price records for one instrument and date, or two distributions for one instrument and ex-date. **Every** record with the same key counts, valid or not: a pair where one record is otherwise invalid reports both codes | Instrument excluded |
| `DATA_DISTRIBUTION_WITHOUT_PRICE` | A distribution whose ex-date has no valid price for that instrument | Instrument excluded |
| `DATA_INVALID_EXCEPTION` | A jump exception with an instrument not in the universe, a date not in the calendar, an empty or blank reason, or an approval that is not a valid ISO date (YYYY-MM-DD) | Entry ignored; reported; `data_ok` false |

Checks run in the table's order for each record; a record that fails one is not checked further. Because duplicates are counted over all records, a distribution on a date whose only price records are duplicates has no valid price and reports `DATA_DISTRIBUTION_WITHOUT_PRICE`. These extra codes only arise for instruments already excluded, so they never change `data_ok`, exclusion or any value.

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

**Provenance.** `exceptions_digest` = SHA-256 (hex) of the UTF-8 bytes of `json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Here `entries` is the list of supplied exception entries, each reduced to the four keys of §2.3, sorted by (instrument, date). The digest covers every supplied entry, valid or not. Every build used for a backtest or a trading decision records `mode`, `exceptions_version` and `exceptions_digest` in the run or experiment registry (§8.1). The raw-dataset manifest does not.

## 8. Storage, manifests and the holdout

### 8.1 Two kinds of provenance (amended in v1.2)

- **Raw dataset** (T-007): the imported records, exactly as validated, stored as Parquet with a **raw-dataset manifest** (§8.4). It carries no exceptions provenance, because no jump exceptions have been applied to it.
- **Build provenance** (T-008 onward): every `build_dataset` run used for a backtest or a trading decision is recorded in the run registry with the raw `dataset_id`, `mode`, `exceptions_version` and `exceptions_digest` (§7.1), and the code commit. Built series are recomputed from the pinned raw dataset rather than stored as authoritative files.

A dataset that fails §8.4 validation cannot be used.

### 8.2 Holdout containment guard

`check_holdout_path(path, repo_root, agent_workspaces)` refuses (`HOLDOUT_PATH_FORBIDDEN`) any path equal to or inside the repository root **or any agent workspace root**. Paths are resolved, including symlinks, and compared by filesystem identity as well as by text (T-006). A sibling whose name merely starts with a root's name is not inside it.

This is a **containment check only**. Passing it does not authorise anyone to create, read or move holdout data.

### 8.3 Holdout isolation boundary (owner-run)

The guard alone cannot keep holdout data away from agents, so these rules apply before any real data is ingested:

1. **No real data is ingested into any agent-accessible location until the charter fixes the holdout dates.**
2. **Any import that could include holdout-period dates is run by the owner, on the owner's machine, outside every agent workspace**, using the single owner command `trader-split` (T-007). Before reading any content, it guards **the source directory, every resolved input file, and the holdout output** against the repository and every agent workspace.
3. **The split writes two partitions:** development (sessions strictly before the holdout start) and holdout. Only the development partition may be placed in an agent-accessible location. Source, development and holdout locations must be **disjoint**: none equal to, inside, or an alias of another.
4. **Each output is published atomically, on its own** (v1.2.1). Each partition is written and fully validated in a staging directory, then renamed into place: holdout first, **development last**. The guarantee is per dataset, not for the pair:
   - A caught failure rolls back: staging directories and any already-renamed output are removed.
   - An **interruption** (crash, kill, power loss) after the holdout rename can leave the holdout output without the development output. This is not a leak: the holdout output is outside every agent location. The development output only ever appears after the holdout output, so agents never see a development dataset from a run whose holdout write failed.
   - **Recovery is the owner's:** a re-run refuses to start while either output or any `<output>.staging-*` directory exists (`SPLIT_OUTPUT_EXISTS`, `SPLIT_STAGING_EXISTS`), naming the leftover paths. The owner deletes them and re-runs.
5. **Agent-run imports** must supply the holdout start and refuse any market event (§8.4) on or after it. Before holdout dates exist, only synthetic data may be imported by an agent.
6. The one-time holdout evaluation is run by the owner (research protocol §3).

### 8.4 Raw-dataset format and validation (v1.2)

A raw dataset is a directory containing **exactly** these files:
- `manifest.json`
- `prices.parquet`
- `distributions.parquet` (may have zero rows)
- `calendar.parquet`
- `declarations.parquet`

**Content identity** (v1.2.1). `dataset_id` is the SHA-256 (hex) of the UTF-8 bytes of:

```
json.dumps({"schema": "trading-bot/raw-dataset/v1",
            "partition": <partition>,
            "holdout_start": <ISO date or null>,
            "files": {<filename>: <file sha256 hex>, ...}},
           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

- The `files` map covers the four Parquet files, keyed by filename.
- `partition` and `holdout_start` are in the identity because they define what the data may be used for. Pinning `dataset_id` therefore pins the partition boundary as well as the files.
- Retrieval time, source label, code commit and writer settings are provenance and are **not** part of the identity. A run that needs them pinned records the SHA-256 of `manifest.json` (`manifest_digest`) alongside `dataset_id`.
- Byte-identical files are only promised under the writer settings and library version pinned in the manifest.

**Market events vs attestation dates.** The partition rules apply to **market events** only:
- price `date`;
- distribution `ex_date`;
- calendar session `date`.

Declaration dates (`corporate_actions_none_through`, `checked_on`) are **attestation dates**: later statements about source quality, not market information available at any historical t. They keep their real values (never backdated) and follow their own rules (§8.5), not the partition rules. `build_dataset` never receives them.

**Manifest fields:** `schema`, `dataset_id`, `partition` (`development` | `holdout` | `synthetic`), `holdout_start` (ISO date, or null only for `synthetic`), `files` (sha256 and row count per file), `date_range` (first and last calendar session), `instruments` (units seen, price rows, distribution rows), and provenance (`source`, `adapter_version`, `code_commit`, `retrieved_at`, `writer` = library name and version and the writer settings).

**Validation on read (never trust the summaries):**
1. `schema` matches exactly, and the directory holds exactly the five files.
2. Every file's SHA-256 and row count match the manifest, and the recomputed `dataset_id` matches.
3. `date_range` and the `instruments` summary are **re-derived from the data** and must equal the manifest.
4. Partition rules, applied to every market event in the price, distribution and calendar files:
   - `development`: all event dates < `holdout_start`;
   - `holdout`: all event dates ≥ `holdout_start`;
   - `synthetic`: every instrument id starts with `SYN_` and `holdout_start` is null.
5. The declarations satisfy §8.5 for the instruments in this dataset.
6. Any failure raises `DataStoreError("DATASET_MANIFEST_MISMATCH", <field>)`, and nothing is returned.

These checks give **integrity** against a pinned manifest, not authenticity. Someone able to replace both the files and the manifest can forge a dataset, so runs pin `dataset_id` (and `manifest_digest` where provenance matters).

### 8.5 Declarations required for real data (v1.2)

Each instrument in an import needs one row in `declarations.csv`, stored as `declarations.parquet`, made by the owner from source evidence:

| Field | Rule |
|---|---|
| `instrument` | In the import |
| `price_semantics` | Must be `unadjusted_close` |
| `distributions_complete` | Must be `true`: every cash distribution in the covered range is in `distributions.csv` (a header-only file then means "no payments") |
| `corporate_actions_none_through` | ISO date ≥ the instrument's last market event date in the import being declared: the source shows **no** split, consolidation or other non-cash corporate action up to this date |
| `evidence_source` | Non-empty (for example the issuer page or the data vendor's corporate-actions feed) |
| `checked_on` | ISO date ≥ `corporate_actions_none_through` (coverage can't be attested before the date it covers) |

These are attestation dates (§8.4): exempt from the partition rules and never backdated. In a split, the declarations made for the full source are **copied unchanged into both partitions**. A development dataset may therefore carry `corporate_actions_none_through` and `checked_on` dates on or after `holdout_start`. On read, the coverage rule is checked against the dataset's own last event date, which a full-source declaration always satisfies.

A missing or invalid declaration refuses the whole import (`IMPORT_DECLARATION_MISSING` / `IMPORT_DECLARATION_INVALID`). If a non-cash corporate action did occur, the instrument cannot be declared and is **unusable until split support is specified**.

The jump check (§7) is an anomaly check, **not** split detection: a 4:3 split lowers the price by exactly 25% and is not flagged. A split-induced jump must never be approved as ordinary cleaning.

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

## 10. Out of scope, and where each is gated

| Item | Gate |
|---|---|
| Downloading from any provider | A broker or vendor adapter card, after feasibility D5 and the holdout dates (§8.3) |
| Share splits and other non-cash corporate actions | Not supported. Real use requires a §8.5 declaration that none occurred; otherwise the instrument is unusable until split support is specified |
| Incomplete distribution history | Real use requires `distributions_complete = true` (§8.5); a missing export is never treated as "no payments" |
| Distributions in a currency other than GBP or GBX | Rejected by `DATA_UNKNOWN_UNIT` |
| Next-session open prices for fills | T-008 (backtester) must extend the canonical record before any backtest result is used |
| FX conversion, intraday data | Not in v1 |
