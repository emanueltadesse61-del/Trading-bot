# 0008 — Owner decisions: universe, robustness variants, stop rule, budget, holdout

Date: 2026-10-16. Decided by: the owner (Samuel), on options and recommendations prepared by Claude. Status: **Confirmed by the owner**. Codex's consistency review at `da35235` (record `8f2190f`) requested one clarification (strategy vs benchmark instruments) and wording alignments, applied below.

All seven decisions were made **before any performance has been computed** on any real data. No backtest exists yet.

## Cross-cutting constraint

The holdout-proposal rule (data spec v1.2.1, T-007 Output 5) needs each instrument to have:
- ≥ 1,009 valid closes before the holdout start H, and
- a 4-year holdout after it.

"About 8 years" is a **screening shorthand**, not the eligibility test. A share class launched after roughly October 2018 can't qualify without proxy history. But an older fund can still fail: the binding test is the actual count of valid closes from the chosen feed, including missing or invalid data. That count is checked for every strategy and benchmark instrument. Proxy history, if ever used, is research-only and reported separately; it is not an automatic remedy.

## Decisions

| # | Item | Decision | Effect |
|---|---|---|---|
| 1 | D1 gold | **Keep gold:** iShares Physical Gold ETC (SGLN) is the **one named non-UCITS exception** | Conditional on the owner's IBKR checks confirming the account can trade it. Charter §6 market row amended |
| 2 | D2 US Treasuries, GBP-hedged | **Drop for v1** | No GBP-hedged candidate passes the screen: VDTS 2022-02-08, GOVP Sep 2019, IGTM Feb 2019. Bonds are covered by UK gilts (VGOV) and index-linked gilts (INXG). A Treasury role may return later only as a new registered trial. See **Instrument sets** below |
| 3 | R-002 trend lookbacks | **3/6/12 months is the primary hypothesis**; **1/3/12 is pre-registered as one robustness variant** | Counts toward the 20-trial budget and is reported whatever it shows. Spec, fixtures and engine unchanged |
| 4 | R-006 rebalancing | **Weekly is primary**, with realised turnover reported; **monthly is pre-registered as a second robustness variant** | Counts toward the budget. Spec unchanged |
| 5 | Research stop rule | **Calendar weeks from Monday 2026-10-19; the checkpoint is Monday 2027-03-08** (week 20) | At the checkpoint the owner asks: has any registered strategy passed Gate 3? If not, either stop, or grant **one** written extension with a reason and a new date. Never a silent continuation |
| 6 | Budget and paper-first | **Confirmed:** £600/year ceiling for data and hosting (a cap, not an approval; each spend needs explicit owner approval). Paper-first confirmed | Planned spend is £0. Real money still needs a separate signed charter section after Gate 5 (charter §2) |
| 7 | Holdout | **Confirmed:** the most recent **4 years**, start computed by the T-007 proposal rule | Sequence: the owner runs `trader-split --propose-holdout` → the owner confirms the date in the charter → the owner runs the split → only then may development data enter an agent-accessible location. The date is fixed before any data reaches an agent and before any performance is computed, never chosen around a market event. If any instrument lacks history, the tool reports it and the owner decides; the holdout is never silently shortened |

## Instrument sets (corrected after Codex's review)

Table B lists eleven strategy-role candidates plus VWRL, which is labelled benchmark-only. Dropping VDTS leaves:

| Set | Instruments | Count |
|---|---|---|
| **Strategy universe** (eligible for portfolio selection) | VUKE, CSP1, VERX, VJPN, VFEM, VGOV, INXG, SGLN, CMOP, IWDP | **10** |
| **Benchmark-only** (never selected by the strategy) | VWRL (global equity buy-and-hold comparison) | 1 |
| **Distinct data instruments** | the two sets above; the 60/40 benchmark reuses VGOV for its gilt leg | **11** |

VWRL is **not** added to portfolio selection. Earlier wording in this record said "11 instruments" for the strategy universe. That was wrong, and is corrected here and in the charter.

## Trial budget after this record

**3 of 20 variants reserved, 0 run:**
- the primary (3/6/12 lookbacks, weekly);
- robustness variant 1: 1/3/12 lookbacks with weekly scheduling, all else fixed;
- robustness variant 2: 3/6/12 lookbacks with monthly scheduling, all else fixed.

The primary is not free. The two comparisons each change **one** thing; combining both changes would be a separate variant and is not included. This record selects the variants but is **not** their pre-registration: each needs its hypothesis file committed under protocol §1 before any backtest runs, and every run gets a registry row.

**One-use holdout.** The comparisons do not each get a fresh final exam. The candidate to take to the holdout is chosen and frozen on development evidence alone, before any holdout inspection, and future hypothesis cards must say so.

## Still open (need evidence first)

- **D5 data source.** Tonight's owner-run, read-only IBKR check returned daily bars for VWRP and IGLT on the unfunded paper login. Those are **not** the configured lines (VWRL, VGOV), so nothing about the chosen instruments is verified yet. Still to check:
  - full-depth history for all 11 data instruments;
  - feed units;
  - split-adjustment semantics of IBKR `TRADES` bars, against data spec §8.5 `unadjusted_close`;
  - distribution history.
- **Instrument history check:** count actual valid closes for every strategy and benchmark instrument against the binding rule. Several share-class inception dates are UNVERIFIED in the feasibility matrix (e.g. CMOP, CSP1, VERX).
- **Declarations** (data spec §8.5): prepared by the owner from source evidence once D5 is settled.
