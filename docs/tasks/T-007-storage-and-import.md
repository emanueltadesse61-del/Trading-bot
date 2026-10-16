## T-007: Raw-dataset storage, canonical CSV import and the owner-run split

**State:** Review, v2 (Codex requirements findings B1–B3 and clarifications resolved in decision 0007). **Codex re-checks before building.**
**Phase:** 1   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** T-006 merged (`98d3bb4`); data spec v1.2 §8 and §10 (this PR). Real-data **use** additionally depends on the owner decisions below; the **build** does not.

### Goal
Make real history storable without breaking isolation:
- one owner-run command that parses, validates and splits a canonical CSV export into a development raw dataset and a holdout raw dataset, published atomically;
- a reader that verifies a raw dataset completely before anything uses it;
- a public import path that refuses holdout-period rows.

A broker- or vendor-specific adapter is a later card.

### Pending owner decisions (gate real-data use only)
| Decision | Proposal / rule |
|---|---|
| Holdout start | Proposed 4 years, computed by the rule in **Output 5** and confirmed by the owner in the charter **before any performance is computed**. It is never chosen around a market event, and is never silently shortened if history is insufficient |
| Data source | Decided after the owner's Table A checks (feasibility D5). IBKR's account approval (2026-10-16) does not by itself establish that the data is adequate |
| Declarations | The owner prepares `declarations.csv` from source evidence (data spec §8.5) |

### Inputs
- `docs/data-spec.md` v1.2: §2–3 records, §8.1–8.5 storage, isolation and declarations, §10 gates
- `trader.data` (T-006): records, `build_dataset`, `check_holdout_path`
- T-006 review notes N2 (`INVALID_MODE`) and N3 (boundary type validation)

### Outputs

**1. Canonical CSV parsing** (`trader/data/csv_import.py`). UTF-8, header row, comma-separated, ISO dates. Four required files:
- `prices.csv`: `instrument,date,close,unit`
- `distributions.csv`: `instrument,ex_date,amount,unit` (header-only allowed)
- `calendar.csv`: `date`
- `declarations.csv`: the §8.5 fields

Internal `parse_csv_dir(directory) -> ParsedImport` does pure parsing and validation; it is used by both paths below. Errors are `DataImportError(code, file, line)`:

| Code | Condition |
|---|---|
| `IMPORT_MISSING_FILE` | A required file is absent |
| `IMPORT_BAD_HEADER` | Missing, extra or duplicated columns |
| `IMPORT_MALFORMED_ROW` | Wrong field count, or bad quoting |
| `IMPORT_BAD_DATE` | Not ISO `YYYY-MM-DD` |
| `IMPORT_BAD_NUMBER` | Not a decimal number. An empty `close` becomes `None`, so `build_dataset` reports `DATA_INVALID_PRICE` |
| `IMPORT_DECLARATION_MISSING` | An instrument in prices or distributions has no declaration row |
| `IMPORT_DECLARATION_INVALID` | A declaration breaks a §8.5 rule, including `corporate_actions_none_through` earlier than the instrument's last record |

Nothing is coerced or skipped silently. Valid-but-wrong data (units, off-calendar dates and so on) is left to `build_dataset` (N3).

**`ParsedImport`** (frozen): `prices`, `distributions`, `calendar`, `declarations`.

**`RawDataset`** (frozen): the same four fields plus `partition` (`development` | `holdout` | `synthetic`) and `holdout_start` (date | None).

**2. Public development import**: `import_csv(directory, *, holdout_start: date | None, synthetic: bool = False) -> RawDataset`.
- `holdout_start=None` without `synthetic=True` → `DataImportError("IMPORT_HOLDOUT_REQUIRED")`.
- `synthetic=True` requires every instrument id to start with `SYN_` (`IMPORT_NOT_SYNTHETIC`), and gives partition `synthetic`.
- Otherwise any dated row on or after `holdout_start`, in any file, gives `IMPORT_HOLDOUT_LEAK` (file, line). The partition is `development`.

**3. Raw-dataset storage** (`trader/data/store.py`, adds `pyarrow`, version pinned in `uv.lock`).

`write_raw_dataset(dataset, directory, *, provenance) -> Manifest`:
- writes the five files of data spec §8.4, rows sorted by (instrument, date) and the calendar by date;
- pins the writer settings (no compression or a named codec, fixed row-group size, no wall-clock metadata);
- computes `dataset_id` exactly as in §8.4.

`provenance` is supplied by the caller: `source`, `adapter_version`, `code_commit`, `retrieved_at`. There is no clock inside.

`read_raw_dataset(directory) -> (RawDataset, Manifest)` performs **every** §8.4 validation step. Any failure → `DataStoreError("DATASET_MANIFEST_MISMATCH", field)`.

**4. Owner-run split**: one command, `trader-split`.

```
trader-split --source DIR --holdout-start YYYY-MM-DD --dev-out DIR --holdout-out DIR \
             --repo-root DIR --agent-workspace DIR [--agent-workspace DIR ...] \
             --source-label TEXT --adapter-version TEXT --retrieved-at ISO8601
```

Order of operations. Nothing is read before step 4.
1. Require at least one `--agent-workspace` (`SPLIT_WORKSPACES_REQUIRED`).
2. **Guard** `--source`, each of the four resolved input files, and `--holdout-out` with `check_holdout_path` against the repo and all workspaces. `--dev-out` may be inside the repo.
3. **Disjointness** (`SPLIT_PATHS_OVERLAP`): source, dev-out and holdout-out must not be equal to, inside, or an alias of one another, judged by both resolved text and filesystem identity. Neither output may already exist (`SPLIT_OUTPUT_EXISTS`).
4. Parse with `parse_csv_dir` (the private full-history path; it prints that it is owner-only).
5. Partition by `holdout_start`: development has every dated row strictly before it, holdout the rest. If either partition has zero calendar sessions, raise `SPLIT_EMPTY_PARTITION`. Declarations go to both partitions.
6. Write each partition to a staging directory (`<out>.staging-<pid>`) beside its target. Read each back with `read_raw_dataset`, and verify that the two partitions' rows exactly partition the source (no row lost or duplicated).
7. Publish by renaming the holdout staging directory, then the development one. If anything fails, remove the staging directories and any partition already renamed, and exit non-zero. **No usable dataset is ever left behind by a failed run.**

`trader-split --propose-holdout --source DIR ...` runs steps 1–4, then prints the Output 5 proposal (or the insufficiency report) and writes nothing.

**5. Holdout proposal rule** (`propose_holdout(parsed, years=4, min_dev_sessions=1009)`):
- **E** = the last calendar session in the import.
- **H** = the first calendar session on or after E's date minus `years` calendar years (same month and day; 29 Feb becomes 28 Feb).
- **Sufficiency:** every declared instrument must have ≥ `min_dev_sessions` valid closes before H (253 warm-up + 756 ≈ 3 years of evaluable development), and at least one valid close on or after H.
- If insufficient, return a report naming each failing instrument and its count, and **no date**. The owner decides (drop the instrument, use proxy history, or amend the charter); the rule never shortens the holdout on its own.

**6. N2:** an unknown `mode` in `build_dataset` raises `InvalidInputError("INVALID_MODE")`. Add the code.

### Evidence
Not applicable (engineering). The 4-year proposal and `min_dev_sessions` are judgements, recorded in the charter when the owner confirms them.

### Constraints
- No network, downloads or broker access. No real market data in the repo or in CI; tests are synthetic only.
- The jump check is not split detection (spec §8.5). Never approve a split-induced jump as cleaning.

### Acceptance criteria
- [ ] **Parsing:** each `IMPORT_*` code is triggered by a test with the expected file and line. A valid synthetic directory parses to records equal to those built in code.
- [ ] **Public import:** `IMPORT_HOLDOUT_REQUIRED` without `holdout_start`; `IMPORT_HOLDOUT_LEAK` for a row on, and a row after, the start in each file; a row the day before is accepted; `IMPORT_NOT_SYNTHETIC` for a non-`SYN_` id in synthetic mode.
- [ ] **Storage:** writing twice gives byte-identical files and the same `dataset_id`; `dataset_id` matches an independent computation of the §8.4 formula.
- [ ] **Storage tamper cases**, each → `DATASET_MANIFEST_MISMATCH` with the field:
  - one changed byte;
  - a missing file, and an extra file;
  - an edited row count;
  - `date_range.last` moved earlier;
  - an edited `instruments` entry;
  - a wrong `schema`;
  - an edited `dataset_id`;
  - a development dataset containing a row on `holdout_start`.
- [ ] **Round trip:** `read_raw_dataset` then `build_dataset` gives the same `DataBuild` as building from the original records.
- [ ] **Split preflight** (synthetic), each refused **before any content is read**, proved with a source whose files would fail to parse:
  - source inside a workspace;
  - a symlinked input file pointing into a workspace;
  - holdout-out inside the repo;
  - dev-out equal to holdout-out;
  - dev-out inside holdout-out;
  - holdout-out inside source;
  - an output already existing;
  - no `--agent-workspace`.

  Plus: an unreadable source file gives a clean failure with nothing published.
- [ ] **Split result:**
  - exact partition;
  - development last date < start; holdout first date ≥ start;
  - both read back cleanly;
  - `SPLIT_EMPTY_PARTITION` when the start is after the last session or on or before the first;
  - a simulated failure during publish leaves no target directory.
- [ ] **Proposal:**
  - a synthetic 7-year history gives the expected H;
  - a 29-Feb E date maps correctly;
  - a short instrument gives an insufficiency report and no date.
- [ ] **Declarations:** missing, invalid `price_semantics`, `distributions_complete=false`, `corporate_actions_none_through` before the last record, and an empty `evidence_source` each refuse the import.
- [ ] `INVALID_MODE` is raised for an unknown mode.
- [ ] `README.md`: a short "importing real data (owner only)" section showing the split and proposal commands and the declarations file.
- [ ] CI green; `docs/handoff.md` updated.

### Exclusions
Broker or vendor adapters, downloads, real data, backtesting (T-008), next-session open prices (T-008), split adjustment.
