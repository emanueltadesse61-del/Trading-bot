## T-009: Experiment registry and pre-registration enforcement

**State:** Review, v3.1 (Codex findings B1–B7 and clarifications resolved; decision 0010 re-review sections). **Codex re-checks before building.**
**Phase:** 2   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** T-008 merged (`7d0e020`); `docs/registry-spec.md` v1.2.1, decision 0010 and `research/hypotheses/H-001.md` (draft), all in this PR.

### Goal
One gate that:
- registers frozen pre-registrations durably, so the trial count can never shrink;
- refuses any real-data run that does not match a registered pre-registration exactly (configuration, period, costs, dataset, cleaning snapshot);
- records every run before and after in an append-only, hash-chained log whose truncation is detectable up to the last committed checkpoint.

**Real-data execution stays refused in this card** (`REGISTRY_REAL_DATA_UNSUPPORTED`) until the open-prices and payment-timing card adds a supported schema. Synthetic runs execute and are recorded.

### Inputs
- `docs/registry-spec.md` v1.2.1 (the authority) and `tests/fixtures/registry_cases.json` v1.1 (Claude's reference vectors)
- `research/hypotheses/H-001.md`; decision 0010; research protocol §1–2; charter §6
- `trader.backtest` (T-008), `trader.data.store.read_raw_dataset` (T-007)

### Outputs
1. **`trader/registry/` package:**
   - `prereg.py`: strict parsing of hypothesis files (spec §1: duplicate keys, non-finite values, exact field sets, roles, schedules, overrides, `frozen_by`, `cost_multipliers`); value validation of resolved `Params` and `BacktestParams` for every declared multiplier (§1.1); the default `resolver` from file to `RunDescriptor`s for variants and baselines.
   - `descriptor.py`: the immutable `RunDescriptor`, `config_hash`, and `build_generator(descriptor)`, which calls the accepted T-008 factories (§2.1). Scripted and custom generators are refused.
   - `exceptions_file.py`: strict parsing of the exceptions snapshot file and its version and digest (§5).
   - `store.py`: SQLite file, triggers, hash chain, `registry_created` genesis, lifecycle checks, `verify_registry(path, checkpoint)` (spec §3), and appends inside `BEGIN IMMEDIATE`.
   - `ops.py`: `register_hypothesis` (§5.1), trial count from events (§5.2), `run_synthetic` (§5.3), `run_registered` with every check and the empty `SUPPORTED_REAL_SCHEMAS` (§5.4), and the run lifecycle with two transactions (§5, §5.5). The clock, git access, `checkpoint_provider` (committed `HEAD` by default) and `resolver` are injectable.
   - `summary.py`: `registry_summary` (§6).
   - CLI `trader-registry` with `init`, `verify`, `checkpoint` and `summary` (§6).
2. **README:** section "Running backtests through the registry", including the checkpoint policy (§3.3) and its limits.

### Constraints
- Synthetic data only. No network, broker, real or holdout data. Registry files live in `tmp_path`, outside the repository root.
- The registry must call the existing `run_backtest` and generators; no second simulator.
- No `Market` is ever built from a raw dataset in this card.
- Nothing here freezes or registers H-001, or edits its contract. `research/registry-checkpoint.json` is **not** created in this card; the owner creates it with `init` when real use begins.

### Acceptance criteria
- [ ] **Fixture:**
  - `chain` reproduces exactly: bodies, `prev_hash`, `row_hash`, non-ASCII note;
  - `verify_registry` accepts it, with and without each checkpoint;
  - every `tamper_cases` entry gives its `code` at its `seq`, or passes where `code` is `null` (the documented limits);
  - the `lifecycle` expectations hold in `registry_summary`;
  - each `config_cases` hash reproduces from its configuration.
- [ ] **Append-only:** SQL `UPDATE` and `DELETE` fail. With the triggers dropped and a row edited, verification still fails.
- [ ] **Durable trial count (B1):**
  - registering a frozen 3-variant file gives `trial_count = 3` with zero runs;
  - then deleting the file, demoting it to `draft`, or renaming it leaves the count at 3, and a run of it is refused (`REGISTRY_HYPOTHESIS_MISSING` or `REGISTRY_HYPOTHESIS_CHANGED`);
  - re-registering the same id gives `REGISTRY_ALREADY_REGISTERED`;
  - a registration that would make 21 gives `TRIAL_BUDGET_EXCEEDED` with no row.
- [ ] **Truncation (B2):** removing the final row is detected against a checkpoint at that row (`REGISTRY_CHECKPOINT_MISMATCH`) and passes internal-only verification (documented). A replacement registry fails the checkpoint.
- [ ] **Binding (B3):** with a registered temporary hypothesis, each refusal happens before any row is written:
  - a changed file (`REGISTRY_HYPOTHESIS_CHANGED`);
  - an unknown variant or baseline;
  - a configuration mismatch (`REGISTRY_CONFIG_MISMATCH`) via an injected **drifted resolver**; the file itself is unchanged, so step 3 passes;
  - an undeclared cost multiplier (e.g. 1.5);
  - a dataset id or digest mismatch;
  - a holdout partition;
  - an exceptions snapshot mismatch, and a malformed exceptions file (`REGISTRY_EXCEPTIONS_FORMAT`: duplicate key, bad `date`, bad or non-round-tripping `approved`, wrong schema);
  - no committed checkpoint (`REGISTRY_CHECKPOINT_MISSING`); a caller cannot substitute an older checkpoint, because the provider reads committed `HEAD`;
  - a dirty checkout.

  `run_registered` has no period or configuration parameter.
- [ ] **Real path blocked (B4):** a request passing every check gives `REGISTRY_REAL_DATA_UNSUPPORTED`. No `run_started` row is written and `run_backtest` is never called; prove both with a spy. This includes a v1 development raw dataset.
- [ ] **Descriptors (B5):**
  - descriptors differing only in `TOP_N`, in one asset class, or in schedule give different `config_hash`es and `variant_id`s;
  - a spy shows `build_generator` received exactly the recorded descriptor and `run_backtest` got `schedule = descriptor.schedule`;
  - a scripted generator gives `REGISTRY_UNSUPPORTED_GENERATOR`.
- [ ] **Value validation (B6):** each gives `REGISTRY_PREREG_INVALID` naming the field:
  - `TOP_N` of 0, −1, `True` and `"4"`;
  - `TREND_LOOKBACKS` `[126, 63, 252]` and `[]`;
  - `MOM_LONG ≤ MOM_SKIP`;
  - sleeves summing to 0.9;
  - `CLASS_CAP` 0;
  - an override `TOP_N: 0` on a robustness variant;
  - a `HALF_SPREAD` valid at m = 1 but giving a non-positive sell price at m = 2.

  H-001's draft passes everything that does not need its nulls.
- [ ] **Synthetic lifecycle:**
  - `completed` with metrics and totals, `error = null`;
  - an ordinary exception gives `failed` with the code, then re-raises;
  - a **child process** killed (`os._exit`) after `run_started` commits leaves an unfinished run that a **separate connection** reads; this proves the two-transaction rule;
  - an unwritable registry after `run_started` raises `REGISTRY_WRITE_FAILED` chained to the original;
  - `supersedes` validated;
  - non-`SYN_` ids refused.
- [ ] **Strict parsing (N1):** a test for each §1 rule: duplicate key, duplicate variant id, `NaN`, unknown key, unknown override field, two primaries, bad schedule, missing `frozen_by` target, `cost_multipliers` without 1.
- [ ] **Concurrency (N2):** two processes registering at once cannot exceed the budget; they are serialised by `BEGIN IMMEDIATE`.
- [ ] **Exceptions-file round trip (B7):** a non-empty file (the spec §5 example entry) parses to `JumpException`s with `date` a `date` and `approved` the **string** `"2026-10-16"`. The shared `exceptions_digest` gives `369a53d5…93db` with no `TypeError`. Feeding the parsed entries to `build_dataset` (a synthetic jump on that date) gives `DATA_JUMP_APPROVED`, not `DATA_INVALID_EXCEPTION`.
- [ ] **Lifecycle verification:** a `run_started` whose `run_id` differs from its `seq`, and a registration whose `trial_count_after` differs from the derived count, each give `REGISTRY_LIFECYCLE` (chain recomputed).
- [ ] **H-001:** the committed draft parses; its field sets match the code; it is refused by `register_hypothesis` (`REGISTRY_HYPOTHESIS_NOT_FROZEN`).
- [ ] Existing tests are unchanged and pass. CI green; `docs/handoff.md` updated.

### Exclusions
Freezing or registering H-001, creating the committed checkpoint, any real-data execution, `market_from_raw`, holdout evaluation, Gate 3 statistics, raw-dataset opens.
