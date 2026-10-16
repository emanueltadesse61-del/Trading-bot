# Backtesting Standards

Status: **Draft — Review (Claude, decision 0004; Codex reviews).** Last updated 2026-10-16.

This is a checklist that every backtest result must satisfy before anyone, human or model, interprets it. Most items are already required by `docs/research-protocol.md`; this document gathers them into one place and adds the few marked **New**. If it disagrees with the research protocol, the protocol wins until the disagreement is resolved in `docs/decisions/`.

## 1. Data integrity

- [ ] Prices come through the data layer, never ad hoc. Dataset manifests are recorded: source, range, hash.
- [ ] One value per session on the exchange calendar; missing closes stay missing (portfolio spec §2–3).
- [ ] **New:** every price is normalised to GBP. Lines quoted in pence (GBX) are divided by 100, and the original unit is recorded (feasibility D3).
- [ ] Total-return series include distributions; tradable prices stay unadjusted (spec §2).
- [ ] Proxy (index) history is labelled and reported **separately** from real-ETF history (protocol §3).
- [ ] Instrument launch dates are respected. No position before a fund existed, unless a labelled proxy is used.
- [ ] A second source agrees on sampled days (Gate 1).

## 2. Timing and leakage

- [ ] Signals at t read only data up to t; the leakage test passes (protocol §4, T-003).
- [ ] Trades fill at the **next session's open**, never at the signal's close.
- [ ] Rebalance day and holiday rules are fixed before any run.

## 3. Costs

- [ ] Base costs: actual commission schedule, half the measured spread per side, slippage (protocol §5).
- [ ] Sensitivity at 2× costs: the result must not turn negative (Gate 3).
- [ ] Turnover and total cost drag are reported for every run.

## 4. Research discipline

- [ ] The hypothesis is pre-registered before the first run, with mechanism, rules, parameters and falsification (protocol §1).
- [ ] **Every** run is in the registry, including failures and abandoned runs. The trial count is shown with every result (protocol §2).
- [ ] An economic rationale is written down. "The model found it" is not a rationale (Bailey & López de Prado 2021).
- [ ] Parameters are fixed in advance. Robustness runs show that nearby values give similar results; they are not a search for the best values.
- [ ] The holdout is untouched until the walk-forward bars pass, then evaluated once by the owner (protocol §3, §6).

## 5. Reporting

Every Gate 3 report contains:

| Item | Notes |
|---|---|
| Net annual return, volatility, Sharpe ratio | From marked-to-market daily equity, after costs, before personal tax |
| Max drawdown and its length | Strategy and benchmark |
| ΔSR vs 60/40 on paired monthly returns, and the bootstrap share of positive paths | Protocol §6. The share is a stability measure, not a probability of edge |
| Simpler-rule comparison | Protocol §6 |
| 2× cost result | Sensitivity only |
| Number of registered trials | Registry count |
| **New: Deflated Sharpe Ratio** | Supplementary, not a gate criterion. It corrects for the number of trials, sample length, skewness and kurtosis (Bailey & López de Prado 2014, 2021). Inputs come from the registry |
| Proxy vs real-ETF split | If any proxy history is used |

## 6. Independent cross-checks (optional, never authoritative)

- Re-compute a buy-and-hold or 60/40 result for one instrument in an outside tool, and investigate any gap larger than rounding.
- Compare the momentum sleeve's broad behaviour with the Kenneth French momentum factor (direction of crashes, rough correlation). Do **not** use factor data as prices.

## 7. AI-agent rules

- A model may implement or review a test. It may not choose which result to report.
- Variants that a model proposes count toward the trial budget like any other.
- No model reads holdout data (`AGENTS.md`).
