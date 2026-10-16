# Research Decision Log

Status: **Draft — Review (Claude, decision 0004; Codex reviews).** Last updated 2026-10-16.

This log records which research findings shaped the specification, which remain uncertain, and why. Technical and process decisions live in `docs/decisions/`; this log covers **research-driven** choices. No backtest or real-data result had been seen when any entry here was written.

| ID | Decision | Evidence | Status |
|---|---|---|---|
| R-001 | Trend following is the core hypothesis | Hurst et al. 2017; Moskowitz et al. 2012 | Adopted as a hypothesis to test |
| R-002 | Trend lookbacks: keep 3/6/12 months, or adopt AQR's 1/3/12? | Hurst et al. 2017 use 1/3/12 monthly; spec v1.2 uses 3/6/12 | **Open — owner decides before pre-registration** |
| R-003 | Momentum holds only positive-return assets | Daniel & Moskowitz 2016 | Adopted (spec v1.1) |
| R-004 | The volatility ceiling is a risk limit, not a return claim | Moreira & Muir 2017 vs Cederburg et al. 2020 | Adopted |
| R-005 | 25% asset and 60% class caps are risk judgements, not evidence-based | No direct evidence | Adopted as a hypothesis |
| R-006 | Weekly rebalancing is kept although the literature is mostly monthly | Literature practice; charter §6 | Open to review at pre-registration |
| R-007 | Plan for weaker results than published | McLean & Pontiff 2016; long-only ETF vs long/short futures | Adopted (affects expectations, not rules) |
| R-008 | Report the Deflated Sharpe Ratio as a supplementary statistic | Bailey & López de Prado 2014, 2021 | Proposed (backtesting standards §5) |
| R-009 | 10-month moving-average rule is the simple baseline | Faber 2007 | Adopted (protocol §6) |
| R-010 | Correction: Chan's *Quantitative Trading* 2nd ed. was published in 2021, not 2026 | Publisher and book listings | Recorded |

## R-002 — Trend lookbacks (open)

**The difference.** AQR's century study combines 1-, 3- and 12-month signals with monthly rebalancing. Our spec uses 3, 6 and 12 months with weekly rebalancing.

**Arguments either way**
- **For 1/3/12:** it matches the most-cited long-sample evidence, and the 1-month signal reacts faster to sharp reversals.
- **For 3/6/12:** fewer signal flips and less turnover, which matters more with weekly rebalancing on ETFs with real spreads. The spec, fixtures and T-003 are already built and accepted on it.

**Recommendation (Claude).** Keep 3/6/12 as the primary pre-registered hypothesis, and register 1/3/12 as **one** pre-specified robustness variant. That variant counts toward the 20-trial budget and is reported whatever it shows. This keeps the accepted spec intact while testing the published construction.

**Who decides.** The owner, with Codex's review, **before** Phase 3 pre-registration. Choosing after seeing data would void the evaluation (research protocol, preamble).

## R-006 — Weekly vs monthly rebalancing (open)

Weekly rebalancing with a 2-point band trades only when drift exceeds the band, so the real trade frequency may be close to monthly. Proposal: keep weekly, report realised turnover, and add monthly rebalancing as a second pre-specified robustness variant if the owner agrees.

## How to add an entry

State the decision, the source (linked in `literature_review.md`), what remains uncertain, and the date. Any entry that changes a rule also needs a numbered record in `docs/decisions/`, dated before the results it affects.
