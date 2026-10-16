## T-005: Data-layer specification and reference cases

**State:** Review (spec and reference cases delivered by Claude; awaiting Codex's check)
**Phase:** 1   **Author:** Claude   **Reviewer:** Codex
**Depends on:** none

### Goal
An exact, source-agnostic definition of how raw daily records become the engine's inputs (`dates`, `tr_close`, `trade_close`, `data_ok`), with independently calculated reference cases for T-006 to be tested against.

### Deliverables (Claude)
- `docs/data-spec.md` v1: outputs, canonical records, record validation, unit conversion, trade close, total-return construction, dataset checks, storage and manifests, holdout guard.
- `tests/fixtures/data_cases.json`: 14 cases (D1–D14), every expected value computed by Claude's own calculator, kept outside the repo.

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
| Any record error | Instrument fully excluded; `data_ok` false. The planner then blocks if it is held, so no sale is caused by bad data | 3 |
| Distributions | Reinvested at the ex-date close; GBX amounts divided by 100 | 4, 6 |
| Abnormal move | Flag above 25% in one session, ignoring distributions; cleared only by a dated, owner-approved exception | 7 |
| Future-dated record | Error (it signals a leakage bug in an adapter) | 3 |
| Holdout path | Refused anywhere inside the repo, including gitignored `data/` | 8 |

### Codex's review task
- [ ] Check the spec is complete and implementable, and consistent with `docs/portfolio-spec.md` §2–3 and the research protocol.
- [ ] Independently reproduce at least **D2, D3, D7, D11, D12 and D14**, outside the repo.
- [ ] Report findings as: blocking / non-blocking, spec section, issue, concrete example.
- [ ] If no blocking findings: mark T-005 **Accepted** in `docs/handoff.md`. T-006 then becomes Ready.

### Exclusions
No implementation code. No data downloads.
