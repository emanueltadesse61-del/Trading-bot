# 0012 — Owner-run IBKR daily-bar export (T-011)

Date: 2026-11-11. Status: **Proposed by Claude.** Codex checks before building; the owner merges. Applies to data spec v1.4 (§2.2, §8.6, §10) and T-011. **Open: U1**, which needs the owner's probe output.

| # | Choice | Why | Alternative considered |
|---|---|---|---|
| 1 | **The export is owner-run, read-only and paper-only.** `readonly=True`; live ports are refused; every managed account must start with IBKR's paper prefix `D`; a fixed allow-list of six API calls | AGENTS.md forbids broker access from agent environments. Read-only plus paper makes an accidental order impossible twice over | Agent-run download: forbidden |
| 2 | **`TRADES` bars with `useRTH=True`** | IBKR states "TRADES data is adjusted for splits, but not dividends". With no corporate action (the §8.5 declaration), split-adjusted equals unadjusted, so the data meets `unadjusted_close`. If a split occurred the instrument is unusable anyway (§8.5) | `ADJUSTED_LAST`: dividend-adjusted, which double-counts our explicit distributions |
| 3 | **Calendar from `exchange_calendars` XLON**, version pinned and recorded | The data spec forbids inferring sessions from records (§2.1). A published, versioned calendar with ad-hoc closures is a supplied source | The union of bar dates: inferred, and misses sessions with no trades |
| 4 | **Contracts pinned by `conId`**, plus an ISIN check where IBKR gives one | Symbol lookups can drift or become ambiguous; the conId is IBKR's stable identity | Symbol only: a silent wrong-line risk |
| 5 | **One-year request windows, at least 11 s apart, oldest first; no automatic retries** | Keeps within IBKR's historical pacing (about 60 requests per 10 minutes). Short windows make a truncated response visible (an empty window is refused). Failing closed avoids partial or duplicated history | Multi-year requests: truncation is hard to detect. Retries: hide pacing violations and change what was retrieved |
| 6 | **An invalid open is written as an empty open (unknown); an invalid close refuses the export** | CSV v2 defines an empty open as unknown, and the backtester cancels that session's order (backtest spec §4), so nothing is invented. A bad close corrupts valuation and returns, so it stops the run | Refuse on any bad open: one bad bar blocks the whole history. Repair from high/low: invents data |
| 7 | **No prices on the console or in the export manifest** | The export contains the holdout years. Owner output pasted into chat must not carry holdout prices into an agent's context (data spec §8.3) | Print a sample bar: convenient, but leaks |
| 8 | **The tool never writes `distributions.csv` or `declarations.csv`** | A tool-written header-only file would mean "no payments" (§8.5) without evidence | Header-only placeholders: a silent completeness claim |
| 9 | **Growth candidates are excluded unless `--include-candidates`** | Short-history candidates (VMID and IWFM from 2014) would constrain the holdout proposal, which is binding on every instrument in the import. The growth proposal is undecided | Always export all 14 |

## U1 — Price units (open; needs the probe)

The data spec (§2.2, feasibility D3) says a record's `unit` comes from the **feed's metadata**, never from a fund name or web page. Several of our lines are quoted in pence on the LSE: CSP1, SGLN, CMOP and IWDP per the feasibility matrix, and EQQQ per the growth proposal. Public reports indicate that market-data feeds often label pence-quoted London lines as `GBP`. If IBKR does this, its metadata alone cannot give the unit, and a pence line read as pounds is wrong by 100×. That changes share counts, the minimum-commission effect and distribution yields.

**The probe** (`ibkr_probe.py`, owner-run, outside the repo) records each contract's `currency`, `priceMagnifier`, `minTick`, ISIN, `conId` and earliest data date. It never requests a price.

Once the output is in, one of these is recorded here before T-011 is Ready:

- **(a) IBKR metadata distinguishes the units** (for example, currency `GBX` or a price magnifier on pence lines). Then `unit_source = feed`, the mapping rule is written here, and the export refuses any row whose declared unit disagrees with the mapped one. The data spec is unchanged.
- **(b) It does not.** Then the owner approves a narrow §2.2 amendment: for IBKR exports, `unit_source = owner_declaration`. The unit is declared per instrument from the exchange listing's quote currency, and `unit_evidence` must record the owner's own check, made on the owner's machine with nothing pasted into chat, that IBKR's latest close matches the LSE quote in that unit. The export still refuses an IBKR currency other than `GBP` or `GBX`.

Claude recommends (a) if the probe supports it, otherwise (b). Either way, a unit is never taken from a fund name alone.
