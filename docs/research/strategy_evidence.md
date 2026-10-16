# Strategy Evidence Map

Status: **Draft — Review (Claude, decision 0004; Codex reviews).** Last updated 2026-10-16.

Every rule in `docs/portfolio-spec.md` v1.2 is listed with the evidence behind it and the gap between that evidence and our implementation.

- **Status = Evidence-backed:** published research supports the idea in a closely related setting.
- **Status = Hypothesis:** a design judgement with no direct evidence. It is tested, not assumed.

Sources are detailed in `literature_review.md`.

## The three questions

| Question | What would establish it | Where it's answered |
|---|---|---|
| Does trend/momentum have a credible historical basis? | Published, long-sample, multi-market evidence | This document (yes, with gaps below) |
| Does our weighting and volatility rule add value beyond a simple benchmark? | Gate 3 on our own data: ΔSR vs 60/40, the simpler-rule test, the holdout | Research protocol §6 (not yet run) |
| Can we implement it reliably? | Spec, reference cases, tests, paper trading | T-002/T-003, Gates 2, 4, 5 |

Only the first question is answered by literature. The other two need our own evidence.

## Rule-by-rule

| Spec rule | Evidence | Gap between the evidence and us | Status |
|---|---|---|---|
| **Trend sleeve**: sign average of 3/6/12-month returns, long-or-cash (§4, §5.1) | Hurst et al. 2017 (1880–2016, 67 markets); Moskowitz et al. 2012 (58 futures) | Evidence is **long/short futures** with leverage; we are **long-only ETFs**, so negative trends give cash, not short gains. Lookbacks differ: AQR uses **1/3/12**, we use 3/6/12 (decision log R-002). Their monthly rebalance vs our weekly | Evidence-backed idea; our variant is a hypothesis |
| **Momentum sleeve**: top 4 by 12-1 month return (§4, §5.2) | Jegadeesh & Titman 1993; Asness et al. 2013 (across asset classes) | Evidence is mostly long/short with many assets. A 12-ETF universe gives a very small cross-section | Evidence-backed idea; small-universe version is a hypothesis |
| **Positive-return filter** on momentum (§4) | Daniel & Moskowitz 2016 (crashes cluster after declines and in high volatility); the dual-momentum idea of combining relative and absolute momentum | Filter not tested in the cited studies in this form. It makes the two sleeves overlap more | Hypothesis, with a risk-control rationale |
| **Inverse-volatility weights** within sleeves (§5.1–5.2) | Hurst et al. size each market to equal volatility; Moreira & Muir 2017 | Inverse vol ignores correlations; equal capital per sleeve, not equal risk | Evidence-backed as common practice |
| **10% portfolio volatility ceiling**, scale down only (§5.6) | Hurst et al. target 10%; Moreira & Muir 2017 (higher Sharpe in factors) | Cederburg et al. 2020: real-time vol management did not reliably beat unmanaged portfolios. We use it **as a risk limit, not a return claim** (R-004). Being unlevered, we never scale up, unlike a true target | Risk control; no return claim |
| **25% asset cap, 60% class cap** (§5.4–5.5) | None specific | Concentration limits are a judgement about worst cases and small-universe risk | Hypothesis / risk control |
| **2-point rebalance band**, actual vs target (§6.3) | General cost-control practice (Carver) | Size of the band is a judgement | Hypothesis; check sensitivity at Gate 3 |
| **Weekly rebalance** (charter §6) | Literature mostly rebalances monthly | Weekly may add turnover and cost; bands limit it | Hypothesis (R-006) |
| **60/40 deciding benchmark** (protocol §5) | Hurst et al. assess trend against 60/40 drawdowns | — | Appropriate comparison |
| **10-month moving-average baseline** (protocol §6) | Faber 2007 | — | Appropriate simple rule |
| **Universe of UCITS ETFs** | Evidence is on futures and indices | ETF costs, tracking error and short histories. Some roles need proxy history (feasibility D2) | Practical constraint |

## What the evidence does **not** tell us

1. How large any edge is for a long-only, unlevered, weekly-rebalanced ETF version. The papers' magnitudes don't carry over.
2. Whether the edge survives our real costs. The papers use their own fee and cost models.
3. Whether the future will look like the past. Published edges decay (McLean & Pontiff 2016), and trend following had a weak 2010s as a group.

These are exactly what Gate 3 and paper trading exist to measure.
