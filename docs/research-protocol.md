# Research Protocol

Status: **Proposed — to be frozen before Phase 3 starts.** Last updated: 2026-10-16.

Once frozen, changes need an entry in `docs/decisions/` dated **before** the affected results are seen. A rule changed after seeing results makes that evaluation void.

## 1. Pre-registration

Before any run on real data, each hypothesis gets a file `research/hypotheses/H-<nnn>.md` containing:

- Mechanism: why the return pattern should exist, who is on the other side, why it may persist.
- Exact rules and every parameter value.
- Expected behaviour (when it should do well and badly).
- Falsification: what result would reject it.
- The comparison and metric it will be judged on (§5).

The file is committed, and its commit hash recorded, before the first run.

## 2. Experiment registry

- Every backtest run writes a registry row automatically: hypothesis ID, variant ID, code commit, config hash, dataset manifest hashes, period, cost setting, metrics, timestamp.
- A **variant** is any change to rules or parameters, including robustness variants and runs abandoned midway. All count toward the **trial budget of 20**.
- Rows are never deleted or edited. A corrected run is a new row that references the old one.
- The variant count is reported alongside every result shown to the owner.

## 3. Data and periods

- Development period: from the first date with full history for the universe, up to the holdout start. Proxy (index) history is allowed for research only and is reported separately from real-ETF results.
- **Holdout:** the most recent **4 years** (owner-confirmed, decision 0008), with the start computed by the T-007 proposal rule. Sequence: owner-only proposal → owner confirms the date in the charter → split → only then may development data enter an agent-accessible location. The date is therefore fixed before any performance is computed.
- The holdout dataset is stored outside the repository and every agent workspace. Only the owner runs the one-time evaluation on it, using the frozen evaluation script at a recorded commit.
- **An inspected holdout is consumed.** It is never treated as unseen again under a new charter, a renamed strategy or a fallback rule.

## 4. Chronological evaluation

- Walk-forward over the development period with an expanding window. v1 has no fitted parameters, so the walk-forward reports performance window by window (one window per calendar year) rather than refitting.
- Signals at date t use data ≤ t. Trades fill at the **next session's open**, never at the close that produced the signal.
- Leakage test (required in CI): changing any data after t must leave all outputs at t unchanged.

## 5. Costs and benchmarks

- **Base costs:** the broker's actual commission schedule, half the measured bid-ask spread per side, and slippage of 5 basis points per side until measured paper fills replace it.
- **Cost sensitivity:** 2× base costs. This tests fragility; it is not a realistic cost model.
- **Deciding benchmark:** 60% global equity ETF / 40% gilt ETF, rebalanced monthly, same cost model.
- **Also reported:** global equity (100% VWRL, bought at the first decision, then monthly band rebalancing, so distributions are reinvested only on a band breach; decision 0009 row 19); the 10-month moving-average rule on the same universe; cash.
- Metrics are computed from marked-to-market daily equity, after costs and before personal tax. Cash earns 0% unless the instrument matrix confirms an accessible rate.

## 6. Gate 3 decision rule

| Element | Rule |
|---|---|
| Primary metric | ΔSR = Sharpe(strategy) − Sharpe(60/40), from paired monthly returns over the walk-forward period |
| Bootstrap statistic | Stationary block bootstrap of the paired monthly returns, mean block length 6 months, 10,000 resamples, fixed seed recorded. Reports the **share of resampled paths with ΔSR > 0**. This describes stability across resamples; it is **not** the probability that the strategy has an edge |
| Simpler-rule test | If the strategy's walk-forward Sharpe does not exceed the 10-month moving-average rule's by at least 0.10, the strategy fails this gate |

**Outcomes.** Evaluate these steps in order and stop at the first that applies. Exactly one outcome results. (Amended by `docs/decisions/0002-t002-review-resolutions.md`.)

| Step | Condition (walk-forward period unless stated) | Outcome |
|---|---|---|
| 1 | Any **hard failure**: ΔSR ≤ 0; simpler-rule test failed; max drawdown worse than the benchmark's; ΔSR ≤ 0 at 2× costs | **Fail** |
| 2 | **Soft shortfall**: ΔSR < +0.20, or positive ΔSR in < 80% of resampled paths | **Inconclusive** (holdout stays unopened) |
| 3 | All walk-forward bars met → open the holdout once. Holdout ΔSR ≤ 0, or holdout drawdown worse than the benchmark's | **Fail** |
| 4 | Otherwise | **Pass** |

- **Pass** permits paper trading only.
- **Inconclusive** means no holdout evaluation and no live money. The frozen strategy may run on paper for 12 months as prospective evidence, registered as a new trial. Only soft shortfalls can lead here; a hard failure never can.
- **Fail** means stop, or start a new charter that inherits the trial count. **Passing walk-forward and then failing the holdout is a Fail**: the better development result never overrides the holdout, and the holdout counts as consumed.

Worked example: ΔSR = 0.30, 90% of paths positive, drawdown and cost stress acceptable, but the strategy beats the moving-average rule by only 0.05. Step 1 applies (simpler-rule test failed), so the outcome is **Fail**, not Inconclusive.

## 7. Fallback strategies

If the strategy fails the simpler-rule test, the moving-average rule does **not** inherit any pass. It is a separate hypothesis that must be pre-registered and pass its own gates. If the holdout has already been inspected, its only remaining source of independent evidence is a new prospective paper period.

## 8. Monitoring after Gate 3

- Expected range: the 5th–95th percentile of rolling 6-month returns from the walk-forward backtest, fixed when Gate 3 is passed.
- Review cadence: monthly summary; formal review every 6 months.
- Live (or paper) 6-month return outside the expected range → pause and review. Never re-optimise against recent losses.
- Operational failures act immediately (architecture §4), regardless of performance.
