# 0008 — Owner decisions: universe, robustness variants, stop rule, budget, holdout

Date: 2026-10-16. Decided by: the owner (Samuel), on options and recommendations prepared by Claude. Status: **Confirmed by the owner**; Codex checks this record for consistency before merge.

All seven decisions were made **before any performance has been computed** on any real data. No backtest exists yet.

## Cross-cutting constraint

The holdout-proposal rule (data spec v1.2.1, T-007 Output 5) needs each instrument to have:
- ≥ 1,009 valid closes before the holdout start H, and
- a 4-year holdout after it.

In practice that is about **8 years of real history**. A share class launched after roughly October 2018 cannot take part without proxy history.

## Decisions

| # | Item | Decision | Effect |
|---|---|---|---|
| 1 | D1 gold | **Keep gold:** iShares Physical Gold ETC (SGLN) is the **one named non-UCITS exception** | Conditional on the owner's IBKR checks confirming the account can trade it. Charter §6 market row amended |
| 2 | D2 US Treasuries, GBP-hedged | **Drop for v1** | No GBP-hedged candidate meets the ~8-year requirement: VDTS 2022-02-08, GOVP Sep 2019, IGTM Feb 2019. Bonds are covered by UK gilts (VGOV) and index-linked gilts (INXG). A Treasury role may return later only as a new registered trial. Universe: **11 instruments** |
| 3 | R-002 trend lookbacks | **3/6/12 months is the primary hypothesis**; **1/3/12 is pre-registered as one robustness variant** | Counts toward the 20-trial budget and is reported whatever it shows. Spec, fixtures and engine unchanged |
| 4 | R-006 rebalancing | **Weekly is primary**, with realised turnover reported; **monthly is pre-registered as a second robustness variant** | Counts toward the budget. Spec unchanged |
| 5 | Research stop rule | **Calendar weeks from Monday 2026-10-19; the checkpoint is Monday 2027-03-08** (week 20) | At the checkpoint the owner asks: has any registered strategy passed Gate 3? If not, either stop, or grant **one** written extension with a reason and a new date. Never a silent continuation |
| 6 | Budget and paper-first | **Confirmed:** £600/year ceiling for data and hosting (a cap, not an approval; each spend needs explicit owner approval). Paper-first confirmed | Planned spend is £0. Real money still needs a separate signed charter section after Gate 5 (charter §2) |
| 7 | Holdout | **Confirmed:** the most recent **4 years**, start computed by the T-007 proposal rule | The exact date is written into the charter **before any performance is computed**, never chosen around a market event. If any instrument lacks history, the tool reports it and the owner decides about that instrument; the holdout is never silently shortened |

## Trial budget after this record

2 of 20 trials are committed to pre-registered robustness variants (1/3/12 lookbacks; monthly rebalancing). The primary hypothesis is the 3rd. Pre-registration (research protocol) must list all three before any backtest runs.

## Still open (need evidence first)

- **D5 data source.** Tonight's owner-run, read-only IBKR check returned daily bars for VWRP and IGLT on the unfunded paper login. Still to check:
  - full-depth history for all 11 instruments;
  - feed units;
  - split-adjustment semantics of IBKR `TRADES` bars, against data spec §8.5 `unadjusted_close`;
  - distribution history.
- **Instrument history check:** confirm every remaining instrument meets the ~8-year requirement. Several share-class inception dates are UNVERIFIED in the feasibility matrix (e.g. CMOP, CSP1, VERX).
- **Declarations** (data spec §8.5): prepared by the owner from source evidence once D5 is settled.
