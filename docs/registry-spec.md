# Experiment Registry and Pre-registration Specification (v1.0)

Status: **Review — awaiting Codex's requirements check (T-009).** Author: Claude. Last updated: 2026-10-16. Implements research protocol §1–2 and charter §6 permanent rule 1. Design choices: `docs/decisions/0010-registry-and-preregistration.md`. Reference vectors: `tests/fixtures/registry_cases.json`.

**Purpose.** Make it impossible to:
- run a strategy variant on real data without a frozen, committed pre-registration;
- lose, edit or hide any run;
- report a result without the trial count.

The registry records evidence; it never decides a gate.

## 1. Pre-registration files (`research/hypotheses/H-<nnn>.md`)

Each file is Markdown, readable by people, containing **exactly one** fenced code block whose info string is `json preregistration`. That block is the machine-readable contract:

| Key | Meaning |
|---|---|
| `id` | `H-001`, `H-002`, … matching the file name |
| `status` | `draft` or `frozen` |
| `frozen_by` | For `frozen`: the decision record that froze it (e.g. `docs/decisions/0011-…`); `null` for `draft` |
| `universe`, `asset_class` | Strategy instruments and classes, exactly as run |
| `benchmarks` | Baseline generator names (backtest spec §6.3) and their instrument ids |
| `params` | Every `Params` field (portfolio spec §1), resolved values |
| `backtest_params` | Every `BacktestParams` field (backtest spec §1), including `HALF_SPREAD` per instrument |
| `variants` | List of `{id, role, overrides, schedule}`. `overrides` holds only the `Params` fields that differ from `params`. `role` is `primary` or `robustness` |
| `cost_stress_multiplier` | 2 (backtest spec §1) |
| `dataset` | `{dataset_id, manifest_digest}` of the pinned development raw dataset, or `null` while draft |
| `period` | `{start, end}` session dates of the evaluation period, or `null` while draft |

**Frozen means complete.** A `frozen` file must have no `null` anywhere in `params`, `backtest_params`, `dataset` or `period`, and every variant must resolve to a complete configuration. Otherwise `REGISTRY_HYPOTHESIS_INCOMPLETE`.

**The prose sections are required and reviewed, but not parsed:**
- mechanism;
- exact rules, with references to the specs;
- expected behaviour;
- falsification;
- comparison and metric (protocol §1).

## 2. Configurations and their hash

For a run, the **configuration** is this canonical object:

`{"schedule", "universe", "asset_class", "params", "backtest_params"}`, with:
- `params` and `backtest_params` resolved in full, the variant's overrides applied;
- `COST_MULTIPLIER` set for this run.

Tuples are written as JSON arrays and frozensets as sorted arrays.

**Canonical JSON** = `json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, encoded as UTF-8. `config_hash` = SHA-256 hex of that encoding (fixture `config_hash_case`).

## 3. Storage

- One SQLite file, **outside the repository** (`REGISTRY_LOCATION` if its resolved path is inside the repository root). Back it up like the ledger (architecture §6).
- One table, `events (seq INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL, body TEXT NOT NULL, row_hash TEXT NOT NULL)`.
- **Append-only, enforced twice:**
  - SQLite `BEFORE UPDATE` and `BEFORE DELETE` triggers abort every change;
  - a **hash chain**: `row_hash = SHA-256(prev_hash + "\n" + body)` over UTF-8, where `body` is the canonical JSON of the event. The first `prev_hash` is 64 zeros.
- `verify_registry(path)` recomputes the chain and checks `seq` is 1, 2, 3, … with no gaps. The first failure raises `RegistryError("REGISTRY_CHAIN_BROKEN", seq)` (fixture `chain` and `tamper_cases`).
- Every write verifies the chain first and appends inside one transaction.

The chain detects edits, deletions and reordering by anyone who cannot recompute every later hash. It is integrity, not authenticity: the owner keeps backups.

## 4. Events

| `type` | When | Body fields (besides `seq`, `type`) |
|---|---|---|
| `run_started` | Before the simulator runs | `run_id` (= this `seq`), `hypothesis_id`, `variant_id`, `kind` (`strategy` or `baseline`), `timestamp_utc`, `code_commit`, `checkout_clean`, `config_hash`, `config`, `data` (`kind`, `dataset_id`, `manifest_digest`, `partition`), `period`, `schedule`, `cost_multiplier`, `exceptions_version`, `exceptions_digest`, `hypothesis_commit`, `hypothesis_sha256`, `supersedes` (an earlier `run_id` or `null`), `note` |
| `run_finished` | After the simulator returns or raises | `run_id`, `outcome` (`completed` or `failed`), `timestamp_utc`, `metrics`, `totals`, `error` (code or `null`) |

A `run_started` with no `run_finished` is an **unfinished run** (abandoned or crashed). It stays in the registry and in every summary. A corrected run is a **new** run whose `supersedes` names the old one; nothing is ever edited.

`timestamp_utc` comes from an injectable clock (ISO 8601 with `Z`), so tests are deterministic.

## 5. Running through the registry

`run_registered(registry_path, *, hypothesis_file | synthetic=True, variant_id | baseline, data, period, cost_multiplier, note, supersedes=None, clock)` performs, in order:

1. `verify_registry`.
2. **Mode checks:**

   | Mode | Requirements |
   |---|---|
   | **Synthetic** | `hypothesis_id = "SYNTHETIC"`. Every instrument id starts with `SYN_` (`REGISTRY_NOT_SYNTHETIC`). A dirty checkout is allowed but recorded (`checkout_clean = false`) |
   | **Real data** | The checkout is clean (`REGISTRY_DIRTY_CHECKOUT`). The hypothesis file is `frozen` and complete; the file is committed and unchanged in the working tree (`REGISTRY_HYPOTHESIS_NOT_FROZEN`). The variant is declared in it (`REGISTRY_UNKNOWN_VARIANT`). The dataset is read with `read_raw_dataset`, and its `dataset_id` and `manifest_digest` equal the file's `dataset` (`REGISTRY_DATASET_MISMATCH`). The partition is `development` (`REGISTRY_HOLDOUT`: holdout evaluation is a separate owner-only card). The period lies inside the dataset |
   | **Hypothesis pinning** | The first run of a hypothesis pins the file's SHA-256. Any later run with a different file content is refused (`REGISTRY_HYPOTHESIS_CHANGED`): a pre-registration cannot be edited after it has been used, only superseded by a new `H-` file |
   | **Trial budget** | Declared strategy variants across all `frozen` files in `research/hypotheses/` must be ≤ 20 (`TRIAL_BUDGET_EXCEEDED`, charter §6) |

3. Append `run_started`.
4. Run `run_backtest` with the resolved configuration.
5. Append `run_finished`: `completed` with metrics and totals, or `failed` with the error code (and the exception is re-raised).

Baseline runs use `kind = "baseline"` and the hypothesis's declared benchmark ids. They never count toward the budget.

A cost-stress run is a run of the **same** variant with `cost_multiplier = 2`; it is not a new variant. The budget counts variants, not runs. Synthetic runs never count.

## 6. Summary (`registry_summary`)

Returns, and every result shown to the owner must carry:
- **`trial_count`**: declared strategy variants in frozen files;
- **variants run** and **runs per variant**;
- completed, failed and unfinished counts;
- any superseded runs.

The CLI `trader-registry verify PATH` and `trader-registry summary PATH --hypotheses DIR` print the same as JSON.

## 7. Errors

`RegistryError(code, detail)`:
- `REGISTRY_LOCATION`, `REGISTRY_CHAIN_BROKEN`, `REGISTRY_NOT_SYNTHETIC`, `REGISTRY_DIRTY_CHECKOUT`;
- `REGISTRY_HYPOTHESIS_NOT_FROZEN`, `REGISTRY_HYPOTHESIS_INCOMPLETE`, `REGISTRY_HYPOTHESIS_CHANGED`, `REGISTRY_UNKNOWN_VARIANT`;
- `REGISTRY_DATASET_MISMATCH`, `REGISTRY_HOLDOUT`, `TRIAL_BUDGET_EXCEEDED`, `REGISTRY_PREREG_FORMAT` (not exactly one `json preregistration` block, or invalid JSON or keys).

Every refusal happens **before** `run_started` is written, so a refused attempt leaves no row. Anything after `run_started` is recorded as `failed`.
