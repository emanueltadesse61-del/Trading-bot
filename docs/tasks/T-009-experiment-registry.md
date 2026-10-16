## T-009: Experiment registry and pre-registration enforcement

**State:** Review, v1. **Codex checks the requirements before building.**
**Phase:** 2   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** T-008 merged (`7d0e020`); `docs/registry-spec.md` v1.0, decision 0010 and `research/hypotheses/H-001.md` (draft), all in this PR.

### Goal
Every backtest that could count as evidence goes through one gate that:
- refuses to run without a frozen pre-registration, a clean checkout and the pinned development dataset;
- records the run before and after in an append-only, hash-chained log;
- reports the trial count with every result.

This card builds the machinery and tests it on synthetic data. H-001 stays a **draft** until the owner freezes it from evidence; no real-data run is possible yet.

### Inputs
- `docs/registry-spec.md` v1.0 (the authority) and `tests/fixtures/registry_cases.json` (Claude's reference vectors)
- `research/hypotheses/H-001.md`; decision 0010; research protocol §1–2; charter §6
- `trader.backtest` (T-008), `trader.data.store.read_raw_dataset` (T-007)

### Outputs
1. **`trader/registry/` package:**
   - `prereg.py`: parse a hypothesis file (exactly one `json preregistration` block; `REGISTRY_PREREG_FORMAT`); validate keys; resolve each variant to a full configuration; check completeness for `frozen` (`REGISTRY_HYPOTHESIS_INCOMPLETE`); count declared strategy variants across a directory.
   - `store.py`: SQLite file with the `events` table, `BEFORE UPDATE` and `BEFORE DELETE` abort triggers, the hash chain, `verify_registry`, and an append inside one transaction after verification. `REGISTRY_LOCATION` for a path inside the repository.
   - `config.py`: canonical JSON and `config_hash` (spec §2).
   - `run.py`: `run_registered` (spec §5), with an injectable clock and git access through a small interface, so tests can fake both.
   - `summary.py`: `registry_summary` (spec §6).
   - CLI `trader-registry verify PATH` and `trader-registry summary PATH --hypotheses DIR` (`project.scripts`).
2. **Docs:** README section "Running backtests through the registry". Decision 0010's backtest-spec amendments are already applied in this PR (v1.2.1).

### Constraints
- Synthetic data only in tests. No network, broker, real or holdout data.
- The registry file is never written inside the repository. Tests use `tmp_path` outside the repository's root.
- `run_registered` must call the existing `run_backtest` and generators. No second simulator.
- Nothing in this card freezes H-001 or edits its contract.

### Acceptance criteria
- [ ] **Fixture:** `chain` reproduces exactly: bodies, `prev_hash` and `row_hash`, including the non-ASCII note. `verify_registry` accepts it. Each `tamper_cases` entry (edit a body, delete a row, swap bodies) raises `REGISTRY_CHAIN_BROKEN` at `first_bad_seq`. `config_hash_case` reproduces.
- [ ] **Append-only:** direct SQL `UPDATE` and `DELETE` on `events` fail (trigger). After the triggers are dropped and a row edited, `verify_registry` still detects it.
- [ ] **Synthetic run:** `run_started` then `run_finished` (`completed`) with metrics; `checkout_clean` recorded. A raising run gives `failed` with the error code, and the exception propagates. An injected crash between the two events leaves an unfinished run that `registry_summary` reports.
- [ ] **Real-data gate**, each refused **before** any row is written:
  - a dirty checkout;
  - a draft file (H-001 as committed);
  - a frozen file with a `null`;
  - an unknown variant;
  - a dataset id or manifest digest mismatch;
  - a holdout-partition dataset;
  - a non-`SYN_` instrument in synthetic mode;
  - a 21st declared variant;
  - a file changed after its first run.

  Use temporary frozen hypothesis files and a synthetic raw dataset in tests.
- [ ] **Accounting:**
  - a cost-stress rerun and a baseline run do not change `trial_count`;
  - three frozen variants give `trial_count = 3` with zero runs;
  - `supersedes` links a correction and both runs remain.
- [ ] **H-001:** the committed file parses; its `params` and `backtest_params` keys equal the `Params` and `BacktestParams` fields; its status is `draft` and it is refused for real data.
- [ ] Existing tests are unchanged and pass. CI green; `docs/handoff.md` updated.

### Exclusions
Freezing H-001, any real-data run, holdout evaluation, Gate 3 statistics (paired monthly ΔSR, bootstrap, walk-forward), raw-dataset opens.
