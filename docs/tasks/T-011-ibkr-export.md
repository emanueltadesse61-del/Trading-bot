## T-011: Owner-run IBKR daily-bar export (`trader-ibkr-export`)

**State:** Draft v1. **Codex checks before building.** One item is open, **U1 (price units)**. It is settled by the owner-run contract probe and recorded in decision 0012 before this card can be Ready.
**Phase:** 2   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** T-010 merged (CSV v2, raw schema v2). Data spec v1.4 (§2.2, §8.6, §10) and decision 0012 (this PR).

### Goal
Give the owner one read-only command that downloads IBKR daily `TRADES` bars for the configured instruments on the owner's own machine. It writes the CSV v2 `prices.csv` and `calendar.csv` that `trader-split` reads, plus an export manifest recording exactly what IBKR returned about each contract. The owner then adds the issuer-sourced `distributions.csv` and the `declarations.csv`, and runs the existing T-007 sequence: propose holdout, confirm it in the charter, split.

**Agents never run this command.** It needs the owner's IB Gateway (no agent environment has broker access, AGENTS.md). Tests use a fake client only.

### Inputs
- `docs/data-spec.md` v1.4: §2.1 calendar, §2.2 units, §8.3 isolation, §8.4.1 CSV v2, §8.5 declarations, **§8.6 IBKR export (new)**, §10.
- Decision 0012 (this PR), decisions 0007 and 0008.
- Existing code: `trader.data.csv_import` (CSV v2), `trader.data.holdout.check_holdout_path`, `trader.data.split` (staging, publication and the clean-commit pattern).
- The owner's probe output: `ibkr_probe.py`, run outside the repo, prints contract metadata only and no prices. It is recorded in decision 0012 §U1.

### Outputs

**1. `config/instruments.csv`** (new, versioned, public facts only). One row per instrument, with these columns:

| Column | Content |
|---|---|
| `instrument` | Ticker used in our data files |
| `role` | `strategy`, `benchmark` or `candidate` |
| `isin` | From the issuer |
| `ibkr_symbol` | IBKR contract symbol |
| `ibkr_exchange` | IBKR exchange |
| `ibkr_currency` | Contract currency |
| `ibkr_conid` | Pinned from the probe |
| `unit` | `GBP` or `GBX` |
| `unit_source` | Per decision 0012 §U1 |
| `unit_evidence` | Non-empty text |

Rows:
- the 10 strategy instruments;
- VWRL (`benchmark`);
- EQQQ, VMID and IWFM (`candidate`, growth proposal PR #16).

The `ibkr_*` and unit values come from the probe and decision 0012. No account identifiers ever go in this file.

**2. `trader/data/ibkr.py` and the console script `trader-ibkr-export`** (owner only).

*Arguments:*
- `--instruments PATH`
- `--out DIR`
- `--end-date YYYY-MM-DD`
- `--repo-root PATH`
- `--agent-workspace PATH` (repeatable)
- `--include-candidates`
- `--host` (default `127.0.0.1`)
- `--port` (default `4002`)
- `--client-id` (default `19`)

*Before connecting:*
- Refuse a dirty checkout (the same check as `trader-split`). Record the commit.
- `--out` must not exist, and neither may any `<out>.staging-*`. Check both with `check_holdout_path` against the repo and every agent workspace (§8.3: the output contains holdout-period data).
- `--end-date` must be an XLON session strictly before today (Europe/London).
- Refuse ports 4001 and 7496, the live Gateway and TWS defaults (`EXPORT_LIVE_PORT`).
- Validate the instruments file (`EXPORT_CONFIG`). Candidates are excluded unless `--include-candidates` is given.

*Connection:* `readonly=True`. Every managed account code must start with `D`, which is IBKR's paper-account prefix; otherwise refuse with `EXPORT_NOT_PAPER`. Account codes are never printed, logged or stored.

*Allowed IBKR calls, exhaustively:* connect, disconnect, `managedAccounts`, `reqContractDetails`, `reqHeadTimeStamp` and `reqHistoricalData`. All calls go through one wrapper exposing only these; a test asserts the module calls nothing else. There are no automatic retries: any failed or timed-out request aborts the export and publishes nothing, and the owner re-runs it.

*Contract check, per instrument:*
- `reqContractDetails(Stock(ibkr_symbol, ibkr_exchange, ibkr_currency))` must return exactly one contract (`EXPORT_CONTRACT_NOT_FOUND` / `EXPORT_CONTRACT_AMBIGUOUS`).
- Its `conId` must equal `ibkr_conid` (`EXPORT_CONTRACT_MISMATCH`).
- If IBKR gives an ISIN, it must equal `isin` (`EXPORT_CONTRACT_MISMATCH`).
- The unit check of decision 0012 §U1 must pass (`EXPORT_UNIT_CONFLICT`).

*History:*
- The start is `reqHeadTimeStamp(whatToShow="TRADES", useRTH=True)`.
- Bars come from `reqHistoricalData(barSizeSetting="1 day", whatToShow="TRADES", useRTH=True, formatDate=1)`. Requests cover one calendar year each, oldest first, with the last one ending at `--end-date`. There are at least 11 seconds between any two historical requests (IBKR pacing: about 60 per 10 minutes).
- A year window after the head timestamp that returns no bars is refused (`EXPORT_HISTORY_GAP`), since that is truncation, not illiquidity.
- Overlapping bars must be identical (`EXPORT_BAR_CONFLICT`).

*Bar validation (data spec §8.6):*

| Case | Result |
|---|---|
| A bar date that is not a `date` | `EXPORT_BAR_DATE` |
| A bar date that is not an XLON session | `EXPORT_OFF_CALENDAR` |
| A bar dated after `--end-date` | `EXPORT_BAR_DATE` |
| A close that is not finite and > 0 | `EXPORT_BAR_INVALID` |
| A close outside `[low, high]` | `EXPORT_BAR_INCONSISTENT` |
| An open that is not finite and > 0, or not within `[low, high]` (exact comparison; `low` and `high` must themselves be finite, > 0 and `low ≤ high`) | Written as an **empty** open (unknown, CSV v2), counted as `opens_unknown` in the manifest and summary. **Never** repaired or replaced |

Nothing is filled, forward-filled, adjusted or dropped.

*Calendar:* `calendar.csv` holds XLON sessions from `exchange_calendars` (version pinned and recorded), from the earliest exported bar to `--end-date`. If the library cannot cover the range, refuse with `EXPORT_CALENDAR_RANGE`.

*Output* (staged as `<out>.staging-<n>`, validated, then renamed to `--out`; any failure removes the staging directory):
- `prices.csv`: CSV v2, `instrument,date,open,close,unit`, sorted by instrument then date. Floats are written as Python `repr` (shortest exact round-trip).
- `calendar.csv`: as above.
- `ibkr_export.json`:
  - tool and module version, code commit, `ib_async` and `exchange_calendars` versions, IBKR server version, `retrieved_at` (UTC);
  - the end date and request parameters;
  - per instrument: the config row, the contract metadata listed in §8.6, the head timestamp, bar count, first and last bar date, sessions without a bar, and `opens_unknown`;
  - the SHA-256 of both CSV files.
  - **No prices and no account codes.**
- The tool does **not** write `distributions.csv` or `declarations.csv`. Their absence makes `trader-split` stop with `IMPORT_MISSING_FILE` until the owner adds them, so a forgotten distribution history can never pass as "no payments".

*Console output:* per instrument, the bar count, first and last date, sessions without a bar and `opens_unknown`, then the output path. **No price, open, close, high or low is ever printed**, so pasted output can't carry holdout information into an agent's context.

**3. Dependencies.** Add an optional extra `ibkr = [ib_async, exchange_calendars]`, pinned in `uv.lock`, and put `exchange_calendars` in the dev group for tests. Core modules must import without the extra: `ib_async` is imported lazily, only in the live path. If `exchange_calendars` cannot be locked alongside the current pins, report back. Do not substitute a hand-made calendar.

**4. README.** The owner sequence:
1. probe;
2. export;
3. add `distributions.csv` from issuer sources, with pay dates (template header);
4. add `declarations.csv`;
5. `trader-split --propose-holdout`;
6. charter;
7. split.

Map the manifest fields to the split's `--source-label`, `--adapter-version` and `--retrieved-at`. Also fix T-010 review note N2: "non-session date", not "weekend".

### Constraints
- No network or broker in tests or CI. Fake client only; real data never enters the repo or any agent workspace.
- Each record keeps one unit (data spec §4). Only `GBP` and `GBX`; FX is out of scope.
- No change to `build_dataset`, the backtester, the registry, fixtures or H-001.

### Acceptance criteria
- [ ] **Guards:** a dirty checkout, an existing `--out` or staging directory, `--out` inside the repo or an agent workspace, a live port, a non-paper account and a non-session or today's `--end-date` are each refused **before** any historical request (the fake records zero requests).
- [ ] **Read-only:** a test proves the module only uses the six allowed calls. A source scan finds no order or account-modifying API names.
- [ ] **Contracts:** each of not found, ambiguous, conId mismatch, ISIN mismatch and unit conflict refuses and publishes nothing.
- [ ] **Bars:**
  - every row of the validation table is tested;
  - an invalid open becomes an empty CSV field and is counted;
  - overlap conflicts, an empty year window and an off-calendar bar are refused;
  - nothing is filled or dropped.
- [ ] **Pacing:** requests are ≥ 11 s apart (using a fake clock); there are no retries.
- [ ] **Output:**
  - `prices.csv` and `calendar.csv` parse through `_parse_csv_dir` as **v2** once a test adds `distributions.csv` and `declarations.csv`;
  - an end-to-end synthetic `SYN_*` export followed by the split gives v2 partitions that `market_from_raw` accepts;
  - without `distributions.csv` the parse fails with `IMPORT_MISSING_FILE`.
- [ ] **Isolation:** neither stdout nor `ibkr_export.json` contains any price value from the fake bars, and neither contains an account code.
- [ ] **Atomicity:** a failure after some instruments leaves no `--out` and no staging directory.
- [ ] **Calendar:** known XLON closures are absent (for example 2022-09-19 and 2023-05-08) and an ordinary session is present.
- [ ] Core imports work without the `ibkr` extra. CI is green; `docs/handoff.md` is updated.

### Exclusions
- Downloading distributions (they come from issuer sources, prepared by the owner).
- Live trading or any order path.
- Split detection or support (§8.5 declarations still decide).
- FX.
- Choosing or confirming the holdout.
- Gate 3 statistics.
- Real-data activation (backtest spec §12).
- Deciding the growth proposal (`--include-candidates` only makes the data available).
