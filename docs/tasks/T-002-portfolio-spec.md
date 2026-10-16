## T-002: Portfolio specification and reference cases

**State:** Review (Claude has delivered; awaiting Codex's check)
**Phase:** 0   **Author:** Claude   **Reviewer:** Codex
**Depends on:** none

### Goal
An exact, unambiguous portfolio algorithm and independently calculated reference cases that T-003 can be tested against.

### Deliverables (done by Claude)
- `docs/portfolio-spec.md`: parameters, eligibility, signals, target weights, order planning, blocked states.
- `tests/fixtures/portfolio_cases.json`: 5 weight cases, 4 order cases, 1 signal case, with every intermediate value.
- `docs/portfolio-reference-cases.md`: human-readable summary and hand working for W1 and O1.

### Ambiguities resolved in the spec
| Topic | Resolution | Spec § |
|---|---|---|
| Ties in momentum ranking | Ascending `id` | 4 |
| Insufficient history | < 253 consecutive closes → ineligible | 3 |
| Zero / tiny volatility | σ < 0.005 → ineligible | 3 |
| Currency | GBP-quoted only in v1; no FX | 2 |
| Class-cap reduction | Proportional within the class | 5.5 |
| Cash | GBP at broker, not an instrument, exempt from caps, zero risk | 5.7 |
| Bands | Actual vs target weight; caps and vol override the band | 6.3 |
| Rounding | Floor with `FLOOR_EPS`; never fractional | 6.4 |
| Settled cash | Buys scaled by k then floored; this run's sale proceeds unused | 6.5 |
| Post-rounding check | One repair pass, then `BLOCKED_CONSTRAINTS` | 6.6–6.7 |
| Held instrument becomes ineligible | `BLOCKED_HELD_INELIGIBLE`, never a forced sale | 3, 6 |

### Codex's review task
- [ ] Read the spec and check it is complete and implementable: every quantity defined, every branch has an outcome, no contradictions with `docs/architecture.md` or `docs/research-protocol.md`.
- [ ] Reproduce **at least W1, W4, O1 and O2 independently** (by hand or with a throwaway script outside the repo) before implementing anything, and report any mismatch with the fixture.
- [ ] Report findings as: blocking / non-blocking, spec section, the issue, a concrete example.
- [ ] If no blocking findings: mark T-002 **Accepted** in `docs/handoff.md`, which moves T-003 to Ready.

### Exclusions
No implementation code in this task.
