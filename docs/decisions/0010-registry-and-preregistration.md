# 0010 — Experiment registry and pre-registration design (T-009)

Date: 2026-10-16. Status: **Proposed by Claude**; Codex checks before building; the owner merges. Applies to `docs/registry-spec.md` v1.0 and `research/hypotheses/H-001.md` (draft).

| # | Choice | Why | Alternative considered |
|---|---|---|---|
| 1 | **One hypothesis (H-001) with three declared variants** (V1 primary, V2 and V3 robustness), not three hypothesis files | The comparisons test the same mechanism. Variant ids are what the registry and protocol §2 count. Replaces backtest spec §12's "H-001…H-003" wording | Three files: duplicates the mechanism text and invites treating comparisons as rival candidates |
| 2 | **Only V1 can pass Gate 3; V2 and V3 can never be promoted** after results are seen | Removes the selection step that would turn 3 trials into "best of 3", and keeps the one-use holdout for the pre-registered candidate (decision 0008) | Pick the best variant: classic multiple-testing bias |
| 3 | **Frozen means complete:** no `null` in parameters, dataset or period | Protocol §1 requires every parameter value before the first run | Freeze now with placeholders: half-spreads and the distribution lag aren't measured yet |
| 4 | **The first run pins the file's hash; later edits are refused** | A pre-registration that can be edited after use isn't one | Allow edits with a note: unverifiable |
| 5 | **Budget = declared strategy variants in frozen files (≤ 20)**; runs of undeclared variants are impossible; stress runs, baselines and synthetic runs never count | Protocol §2 counts variants, including abandoned ones. Declaring before running makes every run attributable | Count runs: penalises the required 2× cost reruns |
| 6 | **SQLite with append-only triggers and a SHA-256 hash chain**, stored outside the repo | Architecture §6. The chain makes edits, deletions and reordering detectable even if the triggers are bypassed | Git-tracked JSON log: would put results in the public repo and still be editable |
| 7 | **Two events per run** (`run_started` before, `run_finished` after); unfinished runs stay visible | An abandoned or crashed run still counts and is shown (protocol §2) | One row at the end: crashes vanish |
| 8 | **Real-data runs need a clean checkout, a frozen file and the pinned dataset; holdout datasets are refused** | Provenance must identify the code and data exactly. The one-time holdout evaluation is a separate owner-only card | Allow holdout runs with a flag: too easy to spend the holdout by accident |
| 9 | **Synthetic runs are recorded too**, as `SYNTHETIC`, with a dirty checkout allowed but flagged | Keeps the machinery exercised and auditable without touching the budget | Not recording them: loses the audit trail of tests that looked like results |

## Amendments

- Backtest spec §12, pre-registration row: "`research/hypotheses/H-001…H-003`" becomes "`research/hypotheses/H-001` with variants V1–V3 (decision 0010)".
- Backtest spec §6.2 (follow-up from Claude's T-008 review, N1): the keys of `targets` are the traded set. An instrument absent from `targets` is **not traded**, even if held; only an explicit `w_i = 0` exits. This matches the implementation and the moving-average rule's "not traded".
