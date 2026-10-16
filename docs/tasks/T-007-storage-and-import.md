## T-007: Storage, manifests, canonical CSV import and the owner-run split

**State:** Review: card drafted by Claude; **Codex checks the requirements before building**
**Phase:** 1   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** T-006 merged (`98d3bb4`). Real-data use additionally depends on the two pending owner decisions below; the code does not.

### Goal
Turn the pure data layer into something that can hold real history safely:
- versioned on-disk datasets with tamper-evident manifests;
- one source-agnostic importer for a canonical CSV format that any vendor export can be converted to;
- the **owner-run split** that keeps the holdout out of every agent workspace (data spec §8.3).

A broker-specific adapter (IBKR) is a later card, after account approval.

### Pending owner decisions (do not block building; block real-data use)
| Decision | Proposal | Rule |
|---|---|---|
| Holdout period | **Proposed: the most recent 4 years** of usable history | Exact start date fixed **mechanically** from usable history: the latest session such that every universe instrument has usable data for both the development and holdout periods. It is written into the charter **before any performance is computed**. The window is **never** chosen to include or exclude a particular market event (Codex correction, 2026-10-16) |
| Data source | IBKR historical bars if adequate (feasibility D5), otherwise an approved alternative | Account approval pending; any paid source needs owner approval (charter §5) |

Until the holdout date is in the charter, the importer refuses non-synthetic use (see `holdout_start` below).

### Inputs
- `docs/data-spec.md` v1.1.1 §2, §3, §8 (manifests, guard, isolation boundary)
- `trader.data` (T-006): `build_dataset`, records, `check_holdout_path`
- Deferred T-006 review notes N2 and N3

### Outputs

**1. Canonical CSV format** (`trader/data/csv_import.py`). UTF-8, header row, comma-separated, ISO dates:
- `prices.csv`: `instrument,date,close,unit`
- `distributions.csv`: `instrument,ex_date,amount,unit` (file optional; absent = no distributions)
- `calendar.csv`: `date`

`import_csv(directory, *, holdout_start, synthetic=False) -> ImportResult` returns typed records and the calendar.

**N3 (boundary validation).** Every row is type-checked at import. A malformed row raises `DataImportError(code, file, line)` with one of:
- `IMPORT_MISSING_COLUMN`: a required column is absent;
- `IMPORT_BAD_DATE`: a date is not ISO `YYYY-MM-DD`;
- `IMPORT_BAD_NUMBER`: a close or amount is not a decimal number. An empty `close` is allowed and becomes `None`, which `build_dataset` then reports as `DATA_INVALID_PRICE`.

Nothing is coerced or skipped silently. Valid-but-wrong data (bad units, off-calendar dates and so on) is left for `build_dataset` to report as usual.

**Holdout leak guard.**
- `holdout_start` is required unless `synthetic=True`.
- Any price, distribution or calendar row dated on or after `holdout_start` raises `DataImportError("IMPORT_HOLDOUT_LEAK", file, line)`, and nothing is returned.
- `synthetic=True` is for tests only. It requires every instrument id to start with `SYN_`, otherwise `IMPORT_NOT_SYNTHETIC`.

This is how an agent-run import is refused before holdout dates exist.

**2. Dataset storage and manifests** (`trader/data/store.py`; adds the `pyarrow` dependency).

`write_dataset(result, out_dir, manifest_path, *, source, adapter_version, code_commit, retrieved_at) -> Manifest` writes Parquet files (`prices.parquet`, `distributions.parquet`, `calendar.parquet`) and a manifest JSON:

```json
{
  "schema": "trading-bot/dataset-manifest/v1",
  "dataset_id": "<sha256 of the sorted file digests, hex>",
  "source": "...", "adapter_version": "...", "code_commit": "...",
  "retrieved_at": "<ISO-8601 UTC, supplied by caller>",
  "date_range": {"first": "YYYY-MM-DD", "last": "YYYY-MM-DD"},
  "holdout_start": "YYYY-MM-DD or null (synthetic)",
  "instruments": {"ID": {"units_seen": ["GBP"], "price_rows": 0, "distribution_rows": 0}},
  "files": {"prices.parquet": {"sha256": "...", "rows": 0}}
}
```

- `retrieved_at` is supplied by the caller, so the function stays deterministic and testable (no clock).
- Rows are written in a fixed order: (instrument, date). The same input therefore gives identical files, digests and `dataset_id`.

`read_dataset(manifest_path, data_dir) -> ImportResult` recomputes every file's SHA-256 and row count. Any mismatch, missing file or extra file raises `DataStoreError("DATASET_MANIFEST_MISMATCH", file)`. A dataset without a matching manifest is never returned.

**3. Owner-run split** (`trader/data/split.py`, CLI entry point `trader-split`).

`split_records(result, holdout_start) -> (development, holdout)`: development holds rows strictly before `holdout_start`; holdout holds the rest, including calendar rows.

`trader-split --source <owner_import_dir> --holdout-start YYYY-MM-DD --dev-out <dir> --holdout-out <dir> --repo-root <path> --agent-workspace <path>...`:
- calls `check_holdout_path(holdout_out, repo_root, agent_workspaces)` **before reading anything**, and fails closed;
- reads the owner's full-history import with `holdout_start=None`. This is the one place a full import is allowed: owner-run, and the CLI prints a warning saying so;
- writes the development dataset and manifest to `--dev-out`, and the holdout dataset and its manifest to `--holdout-out`;
- verifies the written development manifest's `date_range.last` < `holdout_start`, and that the two datasets' rows partition the source exactly (no row lost or duplicated);
- **requires** at least one `--agent-workspace`, so a run that forgets the workspaces is refused (`SPLIT_WORKSPACES_REQUIRED`).

**4. N2:** an unknown `mode` in `build_dataset` raises `InvalidInputError("INVALID_MODE")`. Add the code to `INPUT_ERROR_CODES`.

### Evidence
Not applicable (engineering). The 4-year proposal is a judgement about a sample-size trade-off, recorded in the charter when fixed.

### Constraints
- **Splits and other non-cash corporate actions are not supported.** A split of 1.33:1 or more moves the price ≥ 25% and is caught by the jump check. Such a jump must **not** be cleared with an exception, because the total-return series would be wrong. The dataset is unusable for that instrument until split support is specified. State this in `docs/data-spec.md` §10 and in the `trader-split` warning text.
- Non-GBP/GBX distributions are already rejected by `DATA_UNKNOWN_UNIT`; no change needed.
- No network calls, downloads or broker access anywhere in this card.
- Synthetic fixtures only in tests. **No real market data is committed or used in CI.**

### Acceptance criteria
- [ ] CSV import: a valid synthetic directory round-trips into records equal to those built in code; each `IMPORT_*` code is triggered by a test with the right file and line number.
- [ ] Holdout leak: a row dated on `holdout_start` triggers `IMPORT_HOLDOUT_LEAK`, and so does a row the day after. A row the day before is accepted. Calling without `holdout_start` and without `synthetic=True` is refused.
- [ ] Storage: `write_dataset` twice on the same input gives byte-identical files and the same `dataset_id`.
- [ ] Tamper tests: changing one byte, deleting a file, adding an extra file, or editing a manifest row count each gives `DATASET_MANIFEST_MISMATCH`.
- [ ] `read_dataset` output fed into `build_dataset` gives the same `DataBuild` as building from the original records.
- [ ] Split: development and holdout partition the source exactly; development's last date < `holdout_start`; the guard refuses a `--holdout-out` inside the repo or a workspace **before any file is read** (test with a source directory that would fail to read); a missing `--agent-workspace` is refused.
- [ ] `INVALID_MODE` raised for an unknown mode.
- [ ] `docs/data-spec.md` §10: the split limitation and the "don't clear split jumps" rule recorded. `README.md`: a short "importing real data (owner only)" section describing the split command.
- [ ] CI green; `docs/handoff.md` updated.

### Exclusions
IBKR or any other broker or vendor adapter; downloads; real data; backtesting (T-008); next-session open prices (T-008 extends the data spec).

### Open questions for Codex's requirements check
1. Should `dataset_id` hash the file digests only, or the manifest minus `retrieved_at`? (Draft: file digests only, so re-importing identical data gives the same id.)
2. Is a single `trader-split` CLI enough for the owner, or should the importer and the split be one command so the full history never sits in an intermediate directory?
