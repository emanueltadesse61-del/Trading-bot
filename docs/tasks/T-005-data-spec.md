## T-005: Data-layer specification and reference cases

**State:** Review — v1.1 (Codex findings B1, B2 and the clarifications resolved in decision 0006); awaiting Codex's re-check
**Phase:** 1   **Author:** Claude   **Reviewer:** Codex
**Depends on:** none

### Goal
An exact, source-agnostic definition of how raw daily records become the engine's inputs (`dates`, `tr_close`, `trade_close`, `data_ok`), with independently calculated reference cases for T-006 to be tested against.

### Deliverables (Claude)
- `docs/data-spec.md` v1.1: outputs, canonical records, record validation, unit conversion, trade close, total-return construction, dataset checks, storage and manifests, holdout guard.
- `tests/fixtures/data_cases.json`: 21 cases plus 5 invalid-input cases, every expected value computed by Claude's own calculator, kept outside the repo.

### Evidence
- Feasibility D3: price units come from feed metadata, never inferred.
- Research protocol §3: proxy history is separate; the holdout lives outside the repo.
- Backtesting standards §1: data integrity checklist.
- The 25% jump limit (`JUMP_LIMIT`) is a **hypothesis / judgement**, not evidence-based; it only routes a question to the owner.

### Choices made in the spec (for Codex to challenge)
| Topic | Resolution | Spec § |
|---|---|---|
| Missing session | `None`, never filled; the chain resumes from the last valid price | 6 |
| Stale close at t | `trade_close` `None`, `DATA_STALE` flag, `data_ok` stays true (the engine treats it as `missing_data`) | 5, 7 |
| Any record error | Instrument fully excluded; `data_ok` false, so the planner returns `BLOCKED_DATA` for the whole run, held or not | 3 |
| Distributions | Reinvested at the ex-date close; GBX amounts divided by 100 | 4, 6 |
| Abnormal move | Flag above 25% between consecutive valid prices (may span gaps), ignoring distributions; cleared only by an exception in effect under the mode | 7 |
| Jump approvals | Operational: only if approved ≤ t. Research: a pinned, versioned snapshot with digest | 7.1 |
| Future-dated record | Error (it signals a leakage bug in an adapter) | 3 |
| Holdout path | Refused inside the repo or any agent workspace; an owner-run isolation boundary governs real-data import and the split | 8.2–8.3 |

### Codex's review task
- [ ] Check the spec is complete and implementable, and consistent with `docs/portfolio-spec.md` §2–3 and the research protocol.
- [ ] v1 reproductions stand (D2, D3, D7, D11, D12). For v1.1, independently reproduce **D6, D6b, D6d, D14, D15 and DV5**, plus one `exceptions_digest`.
- [ ] Report findings as: blocking / non-blocking, spec section, issue, concrete example.
- [ ] If no blocking findings: mark T-005 **Accepted** in `docs/handoff.md`. T-006 then becomes Ready.

### Exclusions
No implementation code. No data downloads.
