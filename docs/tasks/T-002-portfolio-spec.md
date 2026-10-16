## T-002: Portfolio specification and reference cases

**State:** Review (spec v1.2 delivered by Claude; awaiting Codex's re-check)
**Phase:** 0   **Author:** Claude   **Reviewer:** Codex
**Depends on:** none

### Goal
An exact, unambiguous portfolio algorithm and independently calculated reference cases that T-003 can be tested against.

### Deliverables (Claude)
- `docs/portfolio-spec.md` v1.2: parameters, inputs and validity, portfolio volatility, eligibility, signals, target weights, order planning, blocked states.
- `tests/fixtures/portfolio_cases.json`: 8 weight, 10 order, 1 signal and 9 invalid-input cases (28), with every intermediate value.
- `docs/portfolio-reference-cases.md`: human-readable summary, with hand working for W1 and O1.
- Decision records `0002` (findings B1–B4, N1, N2) and `0003` (finding B5).

### Ambiguities resolved in the spec (v1.2 section numbers)
| Topic | Resolution | Spec § |
|---|---|---|
| Session calendar and dates | One value per session in `dates`; no alignment; a missing close at t is `missing_data` | 2, 3 |
| Invalid inputs | `InvalidInputError` codes per stage | 2.1 |
| Portfolio volatility numerics | `σ(x) = sqrt(max(0, xᵀΣx))`; below −PSD_TOL raises | 2.2 |
| Currency | GBP-quoted only in v1; no FX | 2 |
| Insufficient history, zero/tiny volatility | Reason codes in a fixed order | 3 |
| Ties in momentum ranking | Ascending `id` | 4 |
| Class-cap reduction | Proportional within the class | 5 (step 5) |
| Cash | GBP at broker, not an instrument, exempt from caps, zero risk | 5 (step 7) |
| Check order and BLOCKED statuses | Fixed table; the first failure decides | 6.1 |
| Held instrument ineligible (including an empty universe) | `BLOCKED_HELD_INELIGIBLE`, never a forced sale | 6.1 |
| Bands | Actual vs target weight; caps and vol override the band | 6.3 (step 3) |
| Rounding | Floor with `FLOOR_EPS`; never fractional | 6.3 (step 4) |
| Settled cash and commission | Buys scaled by k after the commission reserve; this run's sale proceeds unused | 6.3 (step 5) |
| Post-rounding check | Two-sided vol repair; one repeat; nothing new to add → `BLOCKED_CONSTRAINTS` | 6.3 (steps 6–7) |
| Planner scope | Reference-price approximation; Phase 4 risk gate re-checks | 6.4 |

### Codex's review task (v1.2)
- [ ] Re-check spec §2.2 and its use in §5 step 6 and §6.3 steps 3 and 6, against `docs/decisions/0003`.
- [ ] Reproduce W8 and V9 independently, outside the repo.
- [ ] Report findings as: blocking / non-blocking, spec section, the issue, a concrete example.
- [ ] If no blocking findings: mark T-002 **Accepted** in `docs/handoff.md`. T-003 then moves to Ready once PR #1 is merged.

Earlier rounds: v1 reviewed at `c949dfd` (W1, W4, O1, O2 reproduced); v1.1 reviewed at `c457ca5` (S1, O7, O9, V2 reproduced).

### Exclusions
No implementation code in this task.
