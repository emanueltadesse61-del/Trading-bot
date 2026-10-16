## T-004: Account, instrument and data feasibility matrix

**State:** Review — document drafted by Claude under decision 0004 (Codex reviews); broker-dependent checks **Blocked** (IBKR account pending)
**Phase:** 0   **Author:** Claude   **Implementer:** Claude (document, decision 0004), owner (account checks)   **Reviewer:** Codex
**Depends on:** none for the document

### Goal
A single matrix that records what must be true about the account, the instruments and the data before Phase 1, with every unverified item clearly marked as such.

### Inputs
- `docs/charter.md` §3 and §6
- `docs/portfolio-spec.md` §2 (GBP-only, two price series)
- The universe roles listed under Table B

### Output
`docs/feasibility-matrix.md` with three tables. Every cell is one of: a value with its **source and date checked**, `UNVERIFIED`, or `BLOCKED: <reason>`. **Never record a check as passed without a source.**

**Table A — Account checks** (owner performs; Codex lists them and the evidence needed):

| Check | Evidence needed |
|---|---|
| IBKR UK account approved; account type is cash (no margin) | Account settings screenshot or statement, owner-confirmed |
| Paper account available and linked | Paper login works |
| Trading permissions include LSE-listed UCITS ETFs | Permissions page |
| API access enabled for paper | Successful connection from a test script on the owner's machine (not an agent workspace) |
| IB Gateway login method and re-authentication frequency | Owner observation over 2 weeks |
| Market data: what is free, delayed or subscription-only for LSE ETFs, and monthly cost | IBKR market data page + account entitlements |
| Historical daily bars via API: depth available per instrument, pacing limits | Test request results |
| Commission schedule for LSE ETF orders | IBKR pricing page, with date |
| Cash-account settlement: can unsettled sale proceeds fund buys? | IBKR documentation |
| Withdrawals can be disabled for the API user | IBKR documentation or settings |

**Table B — Instrument matrix**, one row per universe role: UK equity, US equity, Europe ex-UK equity, Japan equity, emerging-markets equity, UK gilts, US Treasuries (GBP-hedged if available), inflation-linked bonds, gold, broad commodities, global property, 60/40 benchmark components, global equity benchmark.

Columns: role · candidate fund name · ISIN · exchange and ticker · trading currency · share class (accumulating/distributing) · currency hedging · legal structure (UCITS, KID available) · inception date · ongoing charge · typical spread source · available in account? · history source and first date.

Codex may fill **public** facts (ISIN, inception, charges, structure) from issuer factsheets, citing the URL and date. Account availability stays `BLOCKED` until the owner checks.

**Table C — Historical data options**: source · coverage · total-return or price-only · cost · licence limits · verdict. Include at least IBKR historical data and one free source for research comparison. No purchase without owner approval (charter §5).

### Acceptance criteria
- [ ] All three tables present; no unsourced "yes".
- [ ] Every non-GBP candidate flagged, because v1 accepts GBP-quoted lines only.
- [ ] A short list of decisions the owner must make, each with its cost if any.
- [ ] `docs/handoff.md` updated with which rows are blocked and why.

### Exclusions
No broker connection code in the repo. No downloading of market data into the repo. No subscriptions.

### Open questions
None for the document. The account checks wait on the owner.
