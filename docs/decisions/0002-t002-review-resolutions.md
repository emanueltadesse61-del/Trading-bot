# 0002 — Resolutions to Codex's T-002 review

Date: 2026-10-16. Status: Proposed by Claude; pending Codex re-check and owner merge.
Review: Codex, recorded in `docs/handoff.md` at `3332ccd`, base `c949dfd`.
Changes: `docs/portfolio-spec.md` v1.1, `docs/research-protocol.md` §6, `tests/fixtures/portfolio_cases.json`, `docs/portfolio-reference-cases.md`, `docs/tasks/T-003-portfolio-implementation.md`.

No backtest or real-data result has been seen, so these amendments come before any evidence they could affect.

## B1 — Contradictory all-ineligible outcome — **Accepted**

**Issue.** The v1 summary (§7) said an empty eligible universe exits holdings, while §3 and §6 block on any held ineligible instrument.

**Decision.** Blocking wins. Held instruments are never sold because they are ineligible, including when the eligible set is empty. The spec now separates three situations:

| Situation | Result | Case |
|---|---|---|
| Empty eligible set, something held | `BLOCKED_HELD_INELIGIBLE` | O7 |
| Empty eligible set, nothing held | `OK`, 100% cash, no orders | O6 |
| Eligible instruments with all targets 0 | `OK`, holdings exit via `exit` | O5 |

**Why.** Ineligibility signals untrusted data, and a forced sale on bad data is the failure the architecture forbids. A deliberate universe change is an owner action: sell, then reconfigure.

## B2 — Missing date contract — **Accepted**

**Issue.** Aligning arrays on their last element can treat a stale close as the close at t.

**Decision.** The right-alignment rule is removed. The signal function receives `dates` (the session calendar ending at t) and exactly one value per session per instrument, with missing markers. It never aligns or re-indexes. Building that matrix from dated records is the data layer's responsibility. A missing close at t is `missing_data`. A length mismatch or a duplicate or out-of-order date raises `INVALID_CALENDAR`.

**Evidence.** S1 now carries 253 explicit weekday dates and two new series: STALE (no close at t → `missing_data`) and GAP (one session missing mid-window → `missing_data`). Codex's Thursday/Friday example is exactly STALE.

## B3 — Invalid numeric inputs — **Accepted**

**Decision.** Spec §2.1 lists validity rules per stage. A violation raises `InvalidInputError(code)` at the responsible function. The run records `BLOCKED_INVALID_INPUT` and alerts. Legitimate but untradeable account states are statuses instead:

- `BLOCKED_NAV`: NAV ≤ 0, for example an unfunded account (O8).
- `BLOCKED_UNKNOWN_HOLDING`: a holding outside the universe (O10).

§6.1 fixes the order of all checks, so the first failure decides the result. New invalid-input cases V1–V8 cover NaN σ, an asymmetric covariance matrix, an unknown asset class, a zero price, a fractional holding, negative cash, a duplicate date and a negative price.

## B4 — Gate 3 outcome overlap — **Accepted**

**Decision.** Research protocol §6 now evaluates its steps in a fixed order.

- **Hard failures → Fail:** ΔSR ≤ 0, simpler-rule test failed, worse drawdown, or ΔSR ≤ 0 at 2× costs.
- **Soft shortfalls → Inconclusive:** ΔSR below 0.20, or fewer than 80% of resampled paths positive.
- Only then is the holdout opened; a holdout failure is a Fail.

Codex's example (ΔSR 0.30, simpler-rule margin 0.05) is now unambiguously **Fail**.

## N1 — Fees not reserved — **Accepted now (non-blocking)**

**Decision.** Added `COMMISSION_RESERVE` = £3 per buy order (provisional until T-004) to the settled-cash check:

`k = max(0, cash_settled − reserve × n_buys) / gross`

Spec §6.4 now states that the plan is a reference-price approximation, and that the Phase 4 risk gate re-checks every order against fresh prices, the real fee schedule and live cash.

**Effect on existing cases.** In O1, k changes from 0.86235 to 0.858375 and buy_need from 1507.5 to 1513.5. The orders are unchanged. In O2, buy_need changes from 603 to 606.

## N2 — Fixture coverage — **Accepted**

**Decision.** Added W6, W7, O5–O10, the extended S1, and V1–V8. Every row in spec §7 now has a reference case.

## Additional gap found while resolving these (Claude)

**Issue.** The v1 volatility repair added only over-weight instruments, and v1 step 7 didn't say what happens when a violation remains but nothing can be added. A portfolio holding X at target with its negatively correlated hedge Y unbought (W6/O9) has 12.5% volatility, and no instrument is over-weight.

**Decision.**

- A volatility repair now adds every instrument away from its target, in either direction.
- If violations remain and there is nothing new to add, the result is `BLOCKED_CONSTRAINTS`.

In O9, Y cannot be funded because there is no settled cash, so the plan blocks instead of leaving the account over the volatility ceiling.

## Consequences

T-002 returns to **Review** for Codex to re-check v1.1. Codex reproduces at least S1 (STALE, GAP), O7, O9 and one V case independently. T-003 stays Draft until T-002 is Accepted and T-001 is merged.
