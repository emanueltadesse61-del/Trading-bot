# Experiment Registry and Pre-registration Specification (v1.1)

Status: **Review — v1.1 awaiting Codex's re-check (T-009).** Author: Claude. Last updated: 2026-10-16. Implements research protocol §1–2 and charter §6 permanent rule 1. Design choices: `docs/decisions/0010-registry-and-preregistration.md`. Reference vectors: `tests/fixtures/registry_cases.json` (v1.1). v1.1 resolves Codex's review B1–B4 and N1–N3 (decision 0010, re-review section).

**Purpose:**
- Refuse any real-data run that does not match a frozen, **registered** pre-registration exactly.
- Keep the trial count durable, so it can never shrink.
- Record every run before and after.
- Make edits, reordering and, up to the last committed checkpoint, deletions **detectable**.

Detection has limits (§3.3); nothing here makes loss impossible. The registry records evidence; it never decides a gate.

**v1.x executes synthetic runs only.** Real-data execution is refused (`REGISTRY_REAL_DATA_UNSUPPORTED`, §5.4) until the open-prices and payment-timing card defines a supported raw-dataset schema and the raw-to-market boundary.

## 1. Pre-registration files (`research/hypotheses/H-<nnn>.md`)

Markdown for people, plus **exactly one** fenced block with info string `json preregistration` (`REGISTRY_PREREG_FORMAT` otherwise). The block is parsed strictly:
- duplicate keys are rejected;
- `NaN`, `Infinity` and `-Infinity` are rejected;
- unknown keys are rejected.

| Key | Rule |
|---|---|
| `id` | Equals the file name stem (`H-001`) |
| `status` | `draft` or `frozen` |
| `frozen_by` | `null` if draft. If frozen: a path to an existing `docs/decisions/*.md` file |
| `universe` | Sorted, unique instrument ids |
| `asset_class` | Keys exactly `universe`; values in `params.ASSET_CLASSES` |
| `benchmarks` | Object; keys are among `sixty_forty`, `global_equity`, `moving_average_10m`, `cash`, with their instrument arguments (backtest spec §6.3) |
| `params` | **Exactly** the `Params` fields; it must construct a valid `Params` |
| `backtest_params` | **Exactly** the `BacktestParams` fields **except** `COST_MULTIPLIER`. `HALF_SPREAD` keys are exactly the universe plus the benchmark instruments. It must construct a valid `BacktestParams` |
| `variants` | Non-empty; unique `id`s; exactly one `role: "primary"`, the rest `"robustness"`; `schedule` is `weekly` or `monthly`; `overrides` keys are `Params` fields only, and the resolved `Params` must be valid |
| `cost_multipliers` | The declared set, e.g. `[1, 2]`. It must contain 1; every value finite and > 0 |
| `dataset` | `{dataset_id, manifest_digest}` |
| `period` | `{start, end}` ISO dates, `start < end` |
| `exceptions` | `{version, digest}` of the jump-exceptions snapshot (data spec §7.1) |

Any failure gives `REGISTRY_PREREG_FORMAT`. A **frozen** file additionally must have no `null` anywhere (`REGISTRY_HYPOTHESIS_INCOMPLETE`). A draft may have nulls in `backtest_params`, `dataset`, `period` and `exceptions` only.

The prose sections (mechanism, rules, expected behaviour, falsification, comparison) are required and reviewed, not parsed.

## 2. Configurations

Each variant and each baseline resolves to one **configuration** object, hashed as `config_hash = SHA-256(canonical JSON)`. Canonical JSON = `json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`, UTF-8. Tuples are arrays; frozensets are sorted arrays.

| Kind | Configuration |
|---|---|
| Strategy variant | `{"kind": "strategy", "generator": "strategy", "schedule", "universe", "asset_class", "params" (overrides applied), "backtest_params"}` |
| Baseline | `{"kind": "baseline", "generator": <name>, "schedule": "monthly", "instruments": <its arguments>, "params", "backtest_params"}`. The moving-average rule also includes `"universe"` |

`COST_MULTIPLIER` is **not** part of a configuration. It is a separate run field, checked against the registered set. Fixture `config_cases` gives full vectors for two strategy variants and one baseline.

Baseline ids are `B:<generator>` (e.g. `B:sixty_forty`).

## 3. Storage and verification

### 3.1 The file

- One SQLite file **outside the repository** (`REGISTRY_LOCATION` if its resolved path is inside the repository root).
- Table `events (seq INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL, body TEXT NOT NULL, row_hash TEXT NOT NULL)`, with `BEFORE UPDATE` and `BEFORE DELETE` triggers that abort.
- `row_hash = SHA-256(prev_hash + "\n" + body)`. The first `prev_hash` is 64 zeros.
- `body` is the canonical JSON of the event, and contains `seq` and `type`.
- **seq 1 is always `registry_created`**, with a random `registry_id` (UUID4), `schema = "trading-bot/registry/v1"` and a timestamp. `trader-registry init PATH` creates it and prints the first checkpoint.

### 3.2 `verify_registry(path, checkpoint=None)`

Checked in order; the first failure raises:

| Check | Error |
|---|---|
| Rows are `seq` 1, 2, 3, … with no gaps; each body's `seq` equals the row's; each `prev_hash` and `row_hash` recomputes | `REGISTRY_CHAIN_BROKEN` (seq) |
| seq 1 is the only `registry_created` | `REGISTRY_CHAIN_BROKEN` |
| **Lifecycle:** event types are known. A `run_finished` names an earlier `run_started` that has no finish yet. A `supersedes` names an earlier `run_started` of the same hypothesis, variant or baseline, and kind. A hypothesis id is registered at most once | `REGISTRY_LIFECYCLE` (seq) |
| **Checkpoint**, if given: seq 1's `registry_id` equals the checkpoint's, and the row at the checkpoint's `seq` exists with the checkpoint's `row_hash` | `REGISTRY_CHECKPOINT_MISMATCH` |

### 3.3 Checkpoints and their limits

- `research/registry-checkpoint.json` = `{registry_id, seq, row_hash}`, committed to the repository through normal review. It contains no results.
- `trader-registry checkpoint PATH` prints the current head.
- **Policy:** a new checkpoint is committed after every registration and after every session of real-data runs. A Gate 3 report must cite a checkpoint whose `seq` covers every run it relies on.
- The `registry_id` in the committed checkpoint is **permanent**. Changing it is a charter-level event that the review must refuse unless an owner decision records why (the charter forbids resetting trial history).

**What is detected:**
- edits, reordering and middle deletions, always;
- truncation or rollback to before the committed checkpoint;
- a replacement registry (its `registry_id` differs).

**What is not:** deletion of rows **after** the last committed checkpoint (fixture `suffix_deletion_behind_mid_checkpoint`). Verification without a checkpoint is internal consistency only (`suffix_deletion_internal_only`).

## 4. Events

| `type` | Body fields (besides `seq`, `type`) |
|---|---|
| `registry_created` | `registry_id`, `schema`, `timestamp_utc` |
| `hypothesis_registered` | `hypothesis_id`, `file_sha256`, `hypothesis_commit`, `frozen_by`, `variants` (`variant_id`, `role`, `schedule`, `config_hash`), `baselines` (`baseline_id`, `config_hash`), `dataset`, `period`, `exceptions`, `cost_multipliers`, `trial_count_after`, `timestamp_utc` |
| `run_started` | `run_id` (= this `seq`), `hypothesis_id`, `variant_id` (a variant id or `B:<generator>`), `kind`, `generator`, `timestamp_utc`, `code_commit`, `checkout_clean`, `config_hash`, `config`, `data` (`kind`, `dataset_id`, `manifest_digest`, `partition`), `period`, `cost_multiplier`, `exceptions` (`version`, `digest`), `hypothesis_commit`, `hypothesis_sha256`, `supersedes`, `note` |
| `run_finished` | `run_id`, `outcome` (`completed` or `failed`), `timestamp_utc`, `metrics`, `totals`, `error` |

`timestamp_utc` comes from an injectable clock (ISO 8601, `Z`).

## 5. Operations

All writing operations run inside one SQLite `BEGIN IMMEDIATE` transaction. That transaction holds the write lock across verification, every check, and the append, so two processes cannot both pass a budget or pin check. Every refusal happens **before** any row is written.

### 5.1 `register_hypothesis(path, hypothesis_file, checkpoint)`

1. `verify_registry` with the committed checkpoint.
2. The checkout is clean (`REGISTRY_DIRTY_CHECKOUT`). The file is committed and unchanged in the working tree, and is `frozen` and complete (`REGISTRY_HYPOTHESIS_NOT_FROZEN`, `REGISTRY_HYPOTHESIS_INCOMPLETE`, `REGISTRY_PREREG_FORMAT`).
3. The id is not already registered (`REGISTRY_ALREADY_REGISTERED`). Identities are immutable: a revised pre-registration is a **new** id.
4. **Trial budget:** the variants already registered plus this file's must be ≤ 20 (`TRIAL_BUDGET_EXCEEDED`).
5. Append `hypothesis_registered` with every variant and baseline `config_hash` and `trial_count_after`.

### 5.2 Trial count

`trial_count` = the number of strategy variants across **all** `hypothesis_registered` events. It is read from the registry only, **never** from the files present.

Deleting, renaming or demoting a hypothesis file, or starting a new charter, never lowers it. Registered variants count whether or not they ever run. Baselines, cost-stress reruns and synthetic runs never count.

### 5.3 Synthetic runs: `run_synthetic(path, *, market, generator, backtest_params, period, cost_multiplier, note, supersedes=None, clock)`

- Every instrument id in the market and the generator starts with `SYN_` (`REGISTRY_NOT_SYNTHETIC`).
- `hypothesis_id = "SYNTHETIC"`; the configuration is derived from `generator` and `backtest_params` per §2.
- A dirty checkout is allowed but recorded (`checkout_clean = false`).
- Synthetic runs never count toward the budget.

### 5.4 Real-data runs: `run_registered(path, *, hypothesis_id, variant_or_baseline, dataset_dir, exceptions_file, cost_multiplier, checkpoint, note, supersedes=None, clock)`

**The caller supplies no configuration, period or generator**: all come from the registered hypothesis. Checks, in order:
1. `verify_registry` with the committed checkpoint.
2. Clean checkout.
3. The hypothesis is registered (`REGISTRY_NOT_REGISTERED`). Its file is present (`REGISTRY_HYPOTHESIS_MISSING`) with exactly the registered `file_sha256` (`REGISTRY_HYPOTHESIS_CHANGED`).
4. The variant or baseline is registered (`REGISTRY_UNKNOWN_VARIANT`). Its configuration resolved from the file equals the registered `config_hash` (`REGISTRY_CONFIG_MISMATCH`).
5. `cost_multiplier` is in the registered set (`REGISTRY_COST_UNDECLARED`).
6. The dataset is read with `read_raw_dataset`. Its id and digest equal the registered ones (`REGISTRY_DATASET_MISMATCH`), and the partition is `development` (`REGISTRY_HOLDOUT`).
7. The exceptions snapshot's version and §7.1 digest equal the registered ones (`REGISTRY_EXCEPTIONS_MISMATCH`).
8. The run uses **exactly** the registered `period`. The caller cannot supply another window; walk-forward windows are computed inside Gate 3 statistics from this single run.
9. **Capability:** the dataset's schema must be in `SUPPORTED_REAL_SCHEMAS`, which is **empty in v1.x**. So `REGISTRY_REAL_DATA_UNSUPPORTED` always. No `Market` is built from v1 raw data, and nothing is written.

The open-prices and payment-timing card will add schema v2 to `SUPPORTED_REAL_SCHEMAS` and define `market_from_raw(raw_dataset, exceptions_snapshot)`.

### 5.5 Run lifecycle (synthetic now; real later)

1. Append `run_started`.
2. Call `run_backtest` with the resolved configuration. This is the existing simulator; there is no second one.
3. Append `run_finished`:
   - **Ordinary exception:** `outcome = "failed"` with the error code, then re-raise.
   - **Process death** (kill, power loss) between steps 1 and 3 leaves an **unfinished** run. It stays visible in every summary and is never relabelled.
   - **Failure logging fails** (the registry is unwritable after `run_started`): raise `RegistryError("REGISTRY_WRITE_FAILED")` chained to the original exception. The run then remains unfinished.

## 6. Summary (`registry_summary(path, checkpoint)`)

Returns:
- `registry_id`, head `seq` and `row_hash`;
- `trial_count` (§5.2);
- registered hypotheses and their variants;
- runs per variant and baseline: completed, failed and unfinished;
- superseded runs.

Every result shown to the owner carries `trial_count` and the checkpoint used.

CLI: `trader-registry init PATH`, `trader-registry verify PATH [--checkpoint FILE]`, `trader-registry checkpoint PATH`, `trader-registry summary PATH --checkpoint FILE`, each printing JSON.

## 7. Errors

`RegistryError(code, detail)`:

| Group | Codes |
|---|---|
| Storage and verification | `REGISTRY_LOCATION`, `REGISTRY_CHAIN_BROKEN`, `REGISTRY_LIFECYCLE`, `REGISTRY_CHECKPOINT_MISMATCH`, `REGISTRY_WRITE_FAILED` |
| Pre-registration files | `REGISTRY_PREREG_FORMAT`, `REGISTRY_HYPOTHESIS_NOT_FROZEN`, `REGISTRY_HYPOTHESIS_INCOMPLETE`, `REGISTRY_ALREADY_REGISTERED`, `REGISTRY_NOT_REGISTERED`, `REGISTRY_HYPOTHESIS_MISSING`, `REGISTRY_HYPOTHESIS_CHANGED` |
| Run binding | `REGISTRY_UNKNOWN_VARIANT`, `REGISTRY_CONFIG_MISMATCH`, `REGISTRY_COST_UNDECLARED`, `REGISTRY_DATASET_MISMATCH`, `REGISTRY_HOLDOUT`, `REGISTRY_EXCEPTIONS_MISMATCH`, `REGISTRY_REAL_DATA_UNSUPPORTED` |
| Other | `REGISTRY_DIRTY_CHECKOUT`, `REGISTRY_NOT_SYNTHETIC`, `TRIAL_BUDGET_EXCEEDED` |
