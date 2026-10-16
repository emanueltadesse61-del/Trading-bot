# 0003 — Numerical handling of portfolio volatility (T-002 finding B5)

Date: 2026-10-16. Status: Proposed by Claude; pending Codex re-check and owner merge.
Review: Codex, [PR #2 comment](https://github.com/emanueltadesse61-del/Trading-bot/pull/2#issuecomment-6206052028), reviewing `c457ca5`; handoff commit `3224f45`.
Changes: `docs/portfolio-spec.md` v1.2 (§2.2 added; §5 step 6, §6.3 steps 3 and 6), `tests/fixtures/portfolio_cases.json` (W8, V9).

## Issue

Spec v1.1 accepted a covariance matrix whose smallest eigenvalue is as low as −`PSD_TOL` (−1e-12), but took `sqrt(xᵀΣx)` unconditionally.

Codex's counterexample: Σ = [[0.04, −0.0400000000005], [−0.0400000000005, 0.04]] has smallest eigenvalue ≈ −5e-13, so it passes validation. With weights [0.25, 0.25], xᵀΣx ≈ −6.25e-14, and the square root is undefined.

## Options considered

1. **Tighten validation to eigenvalue ≥ 0.** Rejected: sample covariances of nearly collinear ETFs routinely show eigenvalues of order −1e-16 from floating-point error, so this would raise false errors on valid data.
2. **Repair Σ (eigenvalue clipping or nearest-PSD projection).** Rejected for v1: it changes the risk model, adds a new parameter, and makes reference values depend on the repair method.
3. **Clamp the quadratic form at 0 within a proven bound, and raise beyond it.** Accepted.

## Decision

One function computes every portfolio volatility (spec §2.2):

```text
σ(x) = sqrt(max(0, q))   where q = xᵀ Σ x
if q < −PSD_TOL:  raise InvalidInputError("INVALID_COVARIANCE")
```

## Why this is sound

- For a symmetric Σ, q ≥ λ_min × ‖x‖².
- Validation guarantees λ_min ≥ −`PSD_TOL`.
- Every weight vector in this system is non-negative and sums to at most 1, because there is no leverage and cash is ≥ 0. So ‖x‖² ≤ (Σx)² ≤ 1, and therefore q ≥ −`PSD_TOL`.

Any q in [−`PSD_TOL`, 0) is rounding noise and is treated as zero variance. A q below −`PSD_TOL` cannot come from validated inputs, so it signals a bug and is raised rather than hidden.

## Evidence

| Case | Input | Expected |
|---|---|---|
| W8_negative_quadratic_boundary | Codex's exact matrix; weights 0.25/0.25 | q ≈ −6.25e-14 → σp = 0, scale 1, weights 0.25/0.25, cash 0.50 |
| V9_eigenvalue_below_tolerance | Off-diagonal −0.04000000001 (λ_min ≈ −1e-11) | `INVALID_COVARIANCE` at validation |

All other fixture cases are unchanged; I compared them value by value with the previous fixture.

## Consequences

- T-002 returns to **Review**.
- Codex re-checks spec §2.2 and reproduces W8 and V9.
- T-003 must route every volatility calculation (targets, actual weights, post-trade) through the single `σ(x)` function.
