# 0009 — Backtest simulator design choices (T-008)

Date: 2026-10-16. Status: **Proposed by Claude**; Codex checks before building; the owner merges. Applies to `docs/backtest-spec.md` v1.0.

These choices are made **before** any backtest has been run on any data, synthetic or real. Each one affects measured performance, so changing it after real results exist is a new registered variant (protocol §2), not an edit.

| # | Choice | Why | Alternative considered |
|---|---|---|---|
| 1 | **Weekly decision = last session of each ISO week; monthly = last session of each calendar month.** The final supplied session is never a decision | Fixed by the calendar alone: holidays move the decision earlier automatically, and no weekday parameter can be tuned | A fixed weekday (e.g. Friday) needs a holiday rule and invites choosing the "best" weekday |
| 2 | **Fill at the next session's open; orders live one session**; a missing open cancels the order | Protocol §4 and standards §2. Carrying orders forward would trade on stale decisions | Fill at the signal's own close: look-ahead, since that price is only known once trading has ended. Fill at the next close: workable, but the protocol fixes the next open |
| 3 | **Cost model:** fill = open × (1 ± (half-spread + slippage)); commission max(£3, 0.05%) on buys and sells; `COST_MULTIPLIER` scales every component | Protocol §5; D4. Doubling the minimum too keeps the stress test honest for a small account, where the minimum dominates | Doubling only proportional costs: understates stress at £10k scale |
| 4 | **T+2 settlement** of sale proceeds (`SETTLEMENT_LAG = 2`) | Current UK equity settlement. The UK plans to move to T+1 (expected October 2027); that would be a parameter change recorded as a variant | T+0: overstates cash availability |
| 5 | **Distributions settle 20 sessions after the ex-date** (`DISTRIBUTION_LAG = 20`) | The canonical record has no pay date. Twenty sessions is a conservative assumption, so distribution cash is never available earlier than real | Same-day credit: optimistic |
| 6 | **Buys are reduced at the fill** to the largest quantity affordable from settled cash including commission | The planner sizes on the previous close with a 0.5% buffer; a larger gap at the open must not overdraw cash | Reject the whole order: needlessly discards most of a valid trade |
| 7 | **Exits are never blocked.** A sale whose commission exceeds its proceeds may make settled cash negative; the strategy is then blocked until it recovers | Matches the planner rule "never block a sale for data reasons", and feasibility D4's £1-exit example. Recorded as `SHORTFALL`, never hidden | Skip tiny sells: leaves positions the strategy wanted to exit |
| 8 | **Missing close: value at the last known close and flag `stale`** | Keeps NAV defined without inventing prices; the flag is reported | Drop the holding from NAV: creates fake drawdowns |
| 9 | **Baselines use a simple band rebalancer**, monthly, with the same 2-point band, cash rules and costs as the strategy | Fair comparison. The strategy planner's volatility ceiling would block a 60/40 portfolio | Exact monthly rebalancing without a band: pays the £3 minimum on every small trade, handicapping the benchmark |
| 10 | **10-month moving-average rule:** equal weight 1/N on the strategy universe for instruments above their 10-month-end average `tr_close` | Faber 2007 (R-009), applied to the same universe as the strategy | Applying it to 60/40 only: not the "same universe" comparison the protocol asks for |
| 11 | **Any instrument-excluding data error over the whole run refuses the run** (`BACKTEST_DATA_EXCLUDED`) | Fail closed: a backtest silently missing an instrument would misstate the strategy | Simulate around it: hides data problems inside a performance number |
| 12 | **Open prices enter the canonical record as an optional field now**; raw-dataset storage refuses them until a data card adds schema v2 | Lets T-008 be built and verified on synthetic data without changing T-007's accepted storage format. Amends data spec §10's gate wording | Changing the raw-dataset schema inside T-008: mixes a storage migration into the simulator card |
| 13 | **Metrics are computed from daily NAV**, with risk-free 0 and 252 sessions a year; Gate 3 statistics come in a later card | Protocol §5; keeps T-008 reviewable | Including the bootstrap and walk-forward now: too large for one review |

## Data spec §10 amendment

The row "Next-session open prices for fills → T-008 must extend the canonical record before any backtest result is used" becomes:

> T-008 adds an optional `open` field to the canonical price record. Raw-dataset storage and CSV import refuse non-`None` opens until a data card adds raw-dataset schema v2. No backtest result on real data is used before that card is merged.
