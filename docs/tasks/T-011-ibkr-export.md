## T-011: Owner-run IBKR daily-bar export (`trader-ibkr-export`)

**State:** Draft v2. Codex's findings B1–B2 and N1–N3 are resolved (decision 0012, re-review section). **Codex re-checks before building.** One item is open, **U1 (price units)**. It is settled by owner evidence and recorded in decision 0012 before this card can be Ready.
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

The `ibkr_*` and unit values are filled **only** from evidence recorded in decision 0012 §U1, never guessed. Until then, Codex builds and tests with a synthetic `SYN_*` instruments file, and the real rows land in a follow-up commit once U1 is recorded. No account identifiers ever go in this file.

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
- `--client-id` (default `19`; `0` is refused with `EXPORT_CONFIG`, because client 0 binds manual orders)

*Before connecting:*
- Refuse a dirty checkout (the same check as `trader-split`). Record the commit.
- `--out` must not exist, and neither may any `<out>.staging-*`. Check both with `check_holdout_path` against the repo and every agent workspace (§8.3: the output contains holdout-period data).
- `--end-date` must be an XLON session strictly before today (Europe/London).
- Refuse ports 4001 and 7496, the live Gateway and TWS defaults (`EXPORT_LIVE_PORT`).
- Validate the instruments file (`EXPORT_CONFIG`). Candidates are excluded unless `--include-candidates` is given.

*Connection: a restricted protocol adapter (B1).* `readonly=True` is a client flag, not server-side enforcement, and ib_async's `IB.connect` itself sends account, position and execution requests. So:
- The adapter **never uses `IB.connect` or any `IB` startup sync.** It uses ib_async's protocol layer (`Client` and its decoder), pinned in `uv.lock`, behind one adapter class.
- **One outbound choke point.** Every message passes through a single send function that reads the message type and refuses anything not on this allowlist:
  - the API handshake (version negotiation) and `startApi`;
  - `reqContractDetails`;
  - `reqHeadTimeStamp` and `cancelHeadTimeStamp`;
  - `reqHistoricalData` and `cancelHistoricalData`;
  - `reqMarketDataType`, with delayed data only.

  A refused message is never written to the socket. The adapter disconnects and the export fails with `EXPORT_FORBIDDEN_REQUEST`. Codex confirms, against the pinned source, the exact type codes and what `Client`'s own connect sends, and lists them in the module. Anything the pinned `Client` sends beyond this list fails the startup test and comes back to Claude; the list is not widened silently.
- **Paper account check before any data request.** The server pushes the managed-account list after `startApi`. It must arrive within a finite timeout, be **non-empty**, and every code must start with `D` (IBKR's paper prefix). Otherwise the export fails with `EXPORT_NOT_PAPER`, with no data request sent. Account codes are never printed, logged, stored or included in an error.
- **What this does and does not prevent.** It prevents this program from sending any order or account request. It does not make the Gateway refuse orders: paper accounts accept simulated orders. The second, server-side layer is the Gateway's **Read-Only API** setting, which the owner keeps ticked (a README precondition, not verifiable through the API).
- **Timeouts and cleanup.** Every request has a finite timeout; the values are an implementation choice and are recorded in the manifest. On timeout or error the adapter sends the matching cancel (allowlisted), disconnects and fails the export. There are no automatic retries. On every exit path the socket is closed.

*Output isolation (B2), set up before connecting and kept until exit:*
- Library and Python logging are silenced for the run, including the `ib_async` loggers, the root logger, `logging.lastResort` and `warnings`. No handler may emit a protocol payload.
- `sys.stdout` and `sys.stderr` are replaced by sinks that discard anything not written through the module's own `emit()`. `emit()` uses fixed templates whose fields are only tickers, dates, integer counts and error codes.
- IBKR error events are recorded as **numeric code plus the instrument they belong to**. Their message text is discarded.
- `sys.excepthook` and the CLI's top-level handler print only `EXPORT_<CODE>` with a safe detail (ticker, date, count). An unexpected exception prints `EXPORT_INTERNAL_ERROR` and the exception **class name only**: no message, traceback or payload.
- The same rules apply to `ibkr_export.json`.
- The README warns the owner never to paste IB Gateway or TWS logs, or API message log files, from an export session: those record returned bars and account codes. Keep the Gateway's "Create API message log file" option off.

*Contract check, per instrument:*
- `reqContractDetails(Stock(ibkr_symbol, ibkr_exchange, ibkr_currency))` must return exactly one contract (`EXPORT_CONTRACT_NOT_FOUND` / `EXPORT_CONTRACT_AMBIGUOUS`).
- Its `conId` must equal `ibkr_conid` (`EXPORT_CONTRACT_MISMATCH`).
- If IBKR gives an ISIN, it must equal `isin` (`EXPORT_CONTRACT_MISMATCH`).
- The unit check of decision 0012 §U1 must pass (`EXPORT_UNIT_CONFLICT`).

*History (N2):*
- The start is `reqHeadTimeStamp(whatToShow="TRADES", useRTH=True)`.
- **Windows.** One per calendar year, inclusive, in Europe/London calendar dates: from the head date's year to the year of `--end-date`, oldest first. The first window starts on 1 January of the head year; the last ends on `--end-date`.
- **Requests.** Each window is one request with `barSizeSetting="1 day"`, `whatToShow="TRADES"`, `useRTH=True` and `formatDate=1`, ending at 23:59:59 Europe/London on the window's last day. The duration is long enough to cover the whole window (an implementation choice, for example `2 Y`). Requests are at least 11 seconds apart; IBKR's pacing allows about 60 per 10 minutes.
- **Filtering and duplicates.**
  - Bars dated **before** the window start belong to an earlier window's request and are ignored.
  - A bar dated **after** the window end is refused (`EXPORT_BAR_DATE`), because the request ended there. This includes any bar after `--end-date`.
  - Within one response, identical duplicate dates are kept once; different values for one date fail with `EXPORT_BAR_CONFLICT`.
- **Failure versus empty.**
  - A timeout or an IBKR error fails with `EXPORT_REQUEST_FAILED` and the numeric code.
  - A completed response with no bars inside the window is **empty**. Every window runs from the head year onwards, so an empty window fails with `EXPORT_HISTORY_GAP`.
- **Completeness is not provable from the API.** The manifest and summary report, per instrument:
  - sessions without a bar between the first and last bar;
  - the longest such run;
  - the number of windows.

  The data layer's own checks and the holdout proposal's valid-close count then apply.

*Bar validation (data spec §8.6):*

| Case | Result |
|---|---|
| A bar date that is not a `date` | `EXPORT_BAR_DATE` |
| A bar date that is not an XLON session | `EXPORT_OFF_CALENDAR` |
| A bar dated after `--end-date` | `EXPORT_BAR_DATE` |
| `low` or `high` not finite or ≤ 0, or `low > high` (N1). Checked first: without valid bounds the close cannot be validated | `EXPORT_BAR_INVALID` |
| A close that is not finite and > 0 | `EXPORT_BAR_INVALID` |
| A close outside `[low, high]` (exact comparison) | `EXPORT_BAR_INCONSISTENT` |
| With valid bounds and close: an open that is not finite and > 0, or not within `[low, high]` | Written as an **empty** open (unknown, CSV v2), counted as `opens_unknown` in the manifest and summary. **Never** repaired or replaced |

Nothing is filled, forward-filled, adjusted or dropped.

*Calendar:* `calendar.csv` holds XLON sessions from `exchange_calendars`, a versioned **community-maintained** calendar, not an official exchange publication (N3) (version pinned and recorded), from the earliest exported bar to `--end-date`. If the library cannot cover the range, refuse with `EXPORT_CALENDAR_RANGE`.

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
1. preconditions: Gateway on the paper login, the Read-Only API setting ticked, API message logging off;
2. probe;
3. first export, then the owner-local unit check (decision 0012 §U1) and committing the evidence;
4. the real export from that clean commit;
5. add `distributions.csv` from issuer sources, with pay dates (template header);
6. add `declarations.csv`;
7. `trader-split --propose-holdout`;
8. charter;
9. split.

Map the manifest fields to the split's `--source-label`, `--adapter-version` and `--retrieved-at`. Also fix T-010 review note N2: "non-session date", not "weekend".

### Constraints
- No network or broker in tests or CI. Fake client only; real data never enters the repo or any agent workspace.
- Each record keeps one unit (data spec §4). Only `GBP` and `GBX`; FX is out of scope.
- No change to `build_dataset`, the backtester, the registry, fixtures or H-001.

### Acceptance criteria
- [ ] **Guards:** a dirty checkout, an existing `--out` or staging directory, `--out` inside the repo or an agent workspace, a live port, a non-paper account and a non-session or today's `--end-date` are each refused **before** any historical request (the fake records zero requests).
- [ ] **Restricted adapter (B1)**, tested on the **pinned real `Client`** with a fake transport (a scripted socket), not a fake `IB`:
  - startup sends only the handshake and `startApi`;
  - the managed-account message is required: empty, missing (timeout) and non-`D` lists each give `EXPORT_NOT_PAPER` with zero data requests;
  - client ID 0 is refused;
  - an attempt to send any non-allowlisted message (for example positions, account updates, executions, open orders or placing an order) is blocked before reaching the socket and fails with `EXPORT_FORBIDDEN_REQUEST`;
  - a timeout mid-history sends the cancel, closes the socket and publishes nothing.
- [ ] **Contracts:** each of not found, ambiguous, conId mismatch, ISIN mismatch and unit conflict refuses and publishes nothing.
- [ ] **Bars:**
  - every row of the validation table is tested, including NaN, infinite, zero and inverted high/low;
  - identical duplicates are kept once; bars outside the window are ignored;
  - an invalid open becomes an empty CSV field and is counted;
  - overlap conflicts, an empty year window and an off-calendar bar are refused;
  - nothing is filled or dropped.
- [ ] **Pacing:** requests are ≥ 11 s apart (using a fake clock); there are no retries.
- [ ] **Output:**
  - `prices.csv` and `calendar.csv` parse through `_parse_csv_dir` as **v2** once a test adds `distributions.csv` and `declarations.csv`;
  - an end-to-end synthetic `SYN_*` export followed by the split gives v2 partitions that `market_from_raw` accepts;
  - without `distributions.csv` the parse fails with `IMPORT_MISSING_FILE`.
- [ ] **Output isolation (B2):** with root logging at DEBUG and a capturing handler installed **before** the run, and fake bars and accounts carrying sentinel values (unusual prices and an account code such as `DUSENTINEL42`), test a success, a mid-history request failure and an injected unexpected exception in the decoder. No sentinel appears in:
  - captured stdout or stderr;
  - any log record;
  - the exception output;
  - `ibkr_export.json`.

  The error codes and counts are still printed.
- [ ] **Atomicity:** a failure after some instruments leaves no `--out` and no staging directory.
- [ ] **Units:** a synthetic export with one `GBX` and one `GBP` instrument goes through the split into `build_dataset`, and the GBX closes are divided by 100 (data spec §4) while the GBP closes are unchanged.
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
