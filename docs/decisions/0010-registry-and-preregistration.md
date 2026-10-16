# 0010 — Experiment registry and pre-registration design (T-009)

Date: 2026-10-16. Status: **Proposed by Claude**; Codex checks before building; the owner merges. Applies to `docs/registry-spec.md` v1.1 and `research/hypotheses/H-001.md` (draft). Rows 4–6 amended and rows 10–14 added after Codex's review (see the end).

| # | Choice | Why | Alternative considered |
|---|---|---|---|
| 1 | **One hypothesis (H-001) with three declared variants** (V1 primary, V2 and V3 robustness), not three hypothesis files | The comparisons test the same mechanism. Variant ids are what the registry and protocol §2 count. Replaces backtest spec §12's "H-001…H-003" wording | Three files: duplicates the mechanism text and invites treating comparisons as rival candidates |
| 2 | **Only V1 can pass Gate 3; V2 and V3 can never be promoted** after results are seen | Removes the selection step that would turn 3 trials into "best of 3", and keeps the one-use holdout for the pre-registered candidate (decision 0008) | Pick the best variant: classic multiple-testing bias |
| 3 | **Frozen means complete:** no `null` in parameters, dataset or period | Protocol §1 requires every parameter value before the first run | Freeze now with placeholders: half-spreads and the distribution lag aren't measured yet |
| 4 | **Registration pins the file's hash; later edits are refused, and a revision needs a new id** | A pre-registration that can be edited after registration isn't one | Allow edits with a note: unverifiable |
| 5 | **Budget = strategy variants in `hypothesis_registered` events (≤ 20)**, read from the registry, never from the files present; deleting or demoting a file never lowers it; stress runs, baselines and synthetic runs never count | Protocol §2 and charter rule 1 (never reset). Codex B1 showed a file-based count could fall 3 → 0 | Count files: a deletion erases history |
| 6 | **SQLite with append-only triggers, a SHA-256 hash chain and a committed checkpoint** (`registry_id`, `seq`, `row_hash`) | The chain detects edits, middle deletions and reordering. Only an external checkpoint detects truncation or replacement (Codex B2). Rows after the last checkpoint remain unprotected; this is a stated limit, reduced by checkpointing after every session | Git-tracked JSON log: results in the public repo, still editable |
| 7 | **Two events per run** (`run_started` before, `run_finished` after); unfinished runs stay visible | An abandoned or crashed run still counts and is shown (protocol §2) | One row at the end: crashes vanish |
| 8 | **Real-data runs need a clean checkout, a frozen file and the pinned dataset; holdout datasets are refused** | Provenance must identify the code and data exactly. The one-time holdout evaluation is a separate owner-only card | Allow holdout runs with a flag: too easy to spend the holdout by accident |
| 9 | **Synthetic runs are recorded too**, as `SYNTHETIC`, with a dirty checkout allowed but flagged | Keeps the machinery exercised and auditable without touching the budget | Not recording them: loses the audit trail of tests that looked like results |
| 10 | **Runs are bound to the registered contract:** configuration hash, exact period (no caller-supplied window), declared cost multipliers only, pinned dataset and exceptions snapshot. Baselines have ids (`B:<generator>`) and their own configuration hashes | Recording a changed value is not enforcing a pre-registration (Codex B3) | Record and trust: allows silent window or cost shopping |
| 11 | **Real-data execution refused in v1.x** (`SUPPORTED_REAL_SCHEMAS` empty) until the open-prices and payment-timing card | v1 raw data has no opens, so a "completed" run would be meaningless no-fill noise (Codex B4) | Allow and warn: a warning is not a gate |
| 12 | **Strict pre-registration parsing:** exact field sets, no duplicate keys or non-finite values, one primary, valid overrides, an existing `frozen_by` record | Absence of `null` is not validity (Codex N1) | Lenient parsing |
| 13 | **Lifecycle:** `BEGIN IMMEDIATE` around check-and-append; ordinary exceptions → `failed`; process death → unfinished; logging failure → `REGISTRY_WRITE_FAILED` with the run left unfinished | Codex N2 | "Anything after start is recorded failed": impossible after process death |
| 14 | **Genesis event `registry_created` with a random `registry_id`** | Identifies the registry for checkpoints; a replacement log is detected | Identify by file path: trivially swapped |

## Re-review (Codex at `60623a4`, record `4bcc13b`)

Codex reproduced every hash vector, then raised:
- **B1:** a file-based trial count could shrink. Resolved by registration events and a registry-based count (rows 4, 5).
- **B2:** suffix deletion and replacement were undetected. Resolved by the genesis id and the committed checkpoint, with the limits stated (rows 6, 14).
- **B3:** runs weren't bound to the period, costs or snapshot. Resolved by row 10.
- **B4:** real execution wasn't blocked. Resolved by row 11.

N1–N3 were resolved by rows 12–13, and fixture v1.1 is now full and valid: a genesis event, a registration, full configurations, checkpoints, and suffix-deletion, replacement and lifecycle cases. The stale backtest-spec header was fixed.

## Amendments

- Backtest spec §12, pre-registration row: "`research/hypotheses/H-001…H-003`" becomes "`research/hypotheses/H-001` with variants V1–V3 (decision 0010)".
- Backtest spec §6.2 (follow-up from Claude's T-008 review, N1): the keys of `targets` are the traded set. An instrument absent from `targets` is **not traded**, even if held; only an explicit `w_i = 0` exits. This matches the implementation and the moving-average rule's "not traded".
