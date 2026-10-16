# 0006 — Data spec v1.1: holdout isolation and jump-approval timing (Codex T-005 review)

Date: 2026-10-16. Status: Proposed by Claude; pending Codex re-check and owner merge.
Review: Codex on PR #7 at `3dceea8` (review record `8c4c8a5`, now on the branch).
Changes: `docs/data-spec.md` v1.1, `tests/fixtures/data_cases.json`, the T-005 and T-006 cards.

## B1 — Holdout containment weaker than the protocol — **Accepted**

**Issue.** v1's guard refused only paths inside the repository. Research protocol §3 and `AGENTS.md` also exclude every agent workspace: `/work/Trading-bot-holdout` passed v1, yet sits inside an agent workspace at `/work`. v1 also never said who imports raw data, so a full-history import could expose the holdout before any split.

**Decision.**
- The guard (`check_holdout_path(path, repo_root, agent_workspaces)`) refuses anything inside the repository **or any agent workspace root**. It is declared a containment check only, not an authorisation.
- A new **owner-run isolation boundary** (spec §8.3):
  - no real-data ingestion into agent-accessible locations until the holdout dates are fixed;
  - any import that could include holdout dates is run by the owner, outside agent workspaces;
  - the owner runs the split and copies only the development portion to agents;
  - agent-run adapters must refuse requests reaching the holdout start.
- D14 now lists the agent workspace as a root. `/work/Trading-bot-holdout` and `/work` are refused, while `/work2/holdout` is accepted, as the prefix trap requires.

This enforces the existing rule; it does not require a separate evaluation platform.

## B2 — Jump approval time had no defined effect — **Accepted**

**Issue.** In v1, D6 used an approval dated after t to clear a jump. A later approval could therefore change whether an earlier run traded, which is a leakage hole.

**Options considered.**
- (a) **As-of approval only.** Leakage-safe, but backtests over history could never clean a genuine historical data error, because every approval is later than those dates.
- (b) **Frozen cleaning snapshot only.** Fine for research, but it lets later knowledge into operational decisions.

**Decision: both, by explicit mode** (spec §7.1).
- **Operational** (paper/live): an exception counts only if `approved ≤ t`.
- **Research** (backtests): a versioned, committed snapshot, pinned by `exceptions_version` (required) and `exceptions_digest` (SHA-256 of canonical JSON). The snapshot must be committed before the hypothesis's first registered run, and it is recorded as cleaning, not as information available at t.
- Invalid entries (an unknown instrument, a non-session date, an empty or blank reason, a malformed approval date) are ignored, reported as `DATA_INVALID_EXCEPTION`, and make `data_ok` false.
- An approved jump stays in the report as `DATA_JUMP_APPROVED`, so the audit trail survives.

**Cases:** D6 (research, approval after t → cleared), D6b (operational, approval after t → **not** cleared), D6c (operational, approval by t → cleared), D6d (empty reason), D6e (malformed date) and DV5 (research mode without a version). D5 already covers "no entry in the selected snapshot".

## Non-blocking clarifications — all adopted

- **Blocked status.** A record error sets `data_ok` false, so the accepted planner returns `BLOCKED_DATA` for the **whole run** (portfolio spec §6.1, check 4), held or not. v1 wrongly said `BLOCKED_HELD_INELIGIBLE`. Stale-only data keeps `data_ok` true and reaches the held-ineligible path. T-006 adds composition tests for both.
- **Jumps across gaps.** The check compares consecutive *valid* prices, which may span gaps. That is documented, and D15 (100, missing, 130) is flagged. Nothing is interpolated.
- **Build boundary.**
  - The calendar must be non-empty, strictly increasing and contain t (DV1–DV4 → `INVALID_CALENDAR`).
  - A record dated before the supplied calendar is off-calendar (D16).
  - Records for ids outside the universe are reported as `DATA_UNKNOWN_INSTRUMENT` and make `data_ok` false (D17).
  - Record checks run in a fixed order.
- **Deferred items gated.** Splits, non-GBP distributions, next-open fill prices and real downloads now each name the card that must resolve them before use (spec §10).

## Evidence

- The fixture has 21 cases plus 5 invalid-input cases, all computed by Claude's calculator outside the repo.
- All original cases except D6 and D14 are unchanged value for value (compared programmatically). Each case now also carries `mode`, `exceptions_version` and `exceptions_digest`.
