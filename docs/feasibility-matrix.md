# Feasibility Matrix (T-004)

Status: **Draft — Review (implemented by Claude under decision 0004; Codex reviews).** Public facts checked 2026-10-16. Account checks: **Blocked** until the owner's IBKR account is approved.

Cell values follow the T-004 rule. A cell holds a value with its source, `UNVERIFIED`, or `BLOCKED: <reason>`. **No check is recorded as passed without a source.** Nothing here has been verified inside the owner's account.

## Summary: findings that need owner decisions

| # | Finding | Why it matters | Options | Cost |
|---|---|---|---|---|
| D1 | The GBP gold candidate (iShares Physical Gold, SGLN) is an **ETC, not a UCITS fund**. AJ Bell lists it as "UCITS: No" | The charter universe is UCITS ETFs; an ETC has a different legal structure and issuer exposure, and may count as a complex product for the appropriateness test | (a) Allow a physical gold ETC as the one non-UCITS exception; (b) drop gold from v1 | None |
| D2 | The GBP-hedged US Treasury candidate (Vanguard VDTS) only launched **8 Feb 2022** | About 4.7 years of real history: too short for the development and holdout periods without index proxy data | (a) Use the index as proxy history (reported separately, per research protocol §3); (b) use an unhedged or older Treasury line; (c) drop the role | Possibly index data |
| D3 | Some London lines are quoted in **pence (GBX)**, others in **pounds (GBP)** | Both pass the "GBP-quoted" rule, but the data layer must convert GBX to GBP, or prices are off by 100× | Data-layer rule: normalise every price to GBP and record the original unit | None |
| D4 | IBKR's UK (LSE) commission schedule was **not found on the public pages checked** | `COMMISSION_RESERVE` = £3 is still a placeholder | Owner reads the actual LSE ETF rate in the account's pricing page | None |
| D5 | Paper accounts show **delayed** data for unsubscribed products, and real-time data needs an approved, funded account | Weekly decisions on daily closes don't need real-time data, but the historical-bar depth and cost via the API are unknown | Check API historical bars on the paper account; decide on a paid source only if it falls short | Possibly within the £600/yr ceiling |

## Table A — Account checks (owner performs)

| Check | Evidence needed | Status | Public notes |
|---|---|---|---|
| IBKR UK account approved; cash account (no margin) | Account settings or statement | BLOCKED: account pending | — |
| Paper account available and linked | Paper login works | BLOCKED: account pending | — |
| Permissions: LSE-listed UCITS ETFs (and an ETC, if D1(a)) | Permissions page. Note: options and other complex products are **not** needed | BLOCKED: account pending | — |
| API access enabled for paper | Successful connection from a test script on the owner's machine, not an agent workspace | BLOCKED: account pending | — |
| IB Gateway login method and re-authentication frequency | Owner observation over 2 weeks | BLOCKED: account pending | UNVERIFIED |
| Market data: free, delayed or subscription for LSE ETFs; monthly cost | Market data page and account entitlements | BLOCKED: account pending | Unsubscribed paper data is delayed; real-time subscriptions need an approved, fully funded account ([IBKR](https://www.interactivebrokers.com/en/trading/papertrader-delayed-data.php)) |
| Historical daily bars via API: depth per instrument, pacing limits | Test request results | BLOCKED: account pending | UNVERIFIED |
| Commission for LSE ETF orders (fixed and tiered) | Account pricing page, with date | BLOCKED: account pending | Public pages checked show US and EUR examples only (D4) |
| Can unsettled sale proceeds fund buys in a cash account? | IBKR documentation | UNVERIFIED | The spec does not use them either way (portfolio spec §6.3 step 5) |
| Withdrawals can be disabled for the API user | IBKR documentation or settings | UNVERIFIED | — |
| UK stamp duty on ETF purchases | HMRC or broker statement | UNVERIFIED | Commonly reported as not charged on ETFs; confirm before setting the cost model |

## Table B — Instrument matrix (candidates, not decisions)

Fields come from issuer or broker pages fetched on 2026-10-16. "Charge" is the ongoing charge as displayed; AJ Bell shows it without a unit, and it is read as % a year. **Available in account** is BLOCKED for every row until the owner checks.

| Role | Candidate | ISIN | LSE ticker and quote unit | Income | Charge | Structure | Inception | Source |
|---|---|---|---|---|---|---|---|---|
| UK equity | Vanguard FTSE 100 UCITS ETF (GBP) Distributing | IE00B810Q511 | VUKE, GBP (NAV in GBP) | Distributing, quarterly | 0.09% | Irish UCITS | 22 May 2012 | [Vanguard](https://www.vanguard.co.uk/professional/product/etf/equity/9509/IE00B810Q511) |
| US equity | iShares Core S&P 500 UCITS ETF USD (Acc) | IE00B5BMR087 | CSP1, **pence** | Accumulating | 0.07 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:CSP1) |
| Europe ex-UK equity | Vanguard FTSE Developed Europe ex UK UCITS ETF | IE00BKX55S42 | VERX, £ | Quarterly | 0.1 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE%3AVERX) |
| Japan equity | Vanguard FTSE Japan UCITS ETF | IE00B95PGT31 | VJPN, £ | Quarterly | 0.1 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VJPN) |
| Emerging-markets equity | Vanguard FTSE Emerging Markets UCITS ETF | IE00B3VVMM84 | VFEM, £ | Quarterly | 0.17 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VFEM) |
| UK gilts | Vanguard U.K. Gilt UCITS ETF | IE00B42WWV65 | VGOV, £ | Monthly | 0.05 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VGOV) |
| US Treasuries, GBP-hedged | Vanguard USD Treasury Bond UCITS ETF GBP Hedged Distributing | IE000S0PSP47 | VDTS, GBP | Distributing, monthly | 0.08% | Irish UCITS | **08 Feb 2022** (D2) | [Vanguard](https://www.vanguard.co.uk/professional/product/etf/bond/E024/usd-treasury-bond-ucits-etf-gbp-hedged-distributing) |
| Inflation-linked bonds | iShares £ Index-Linked Gilts UCITS ETF GBP (Dist) | IE00B1FZSD53 | INXG, £ | Semi-annual | 0.1 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:INXG) |
| Gold | iShares Physical Gold ETC | IE00B4ND3602 | SGLN, **pence** | None | 0.12 | **ETC, "UCITS: No"** (D1) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:SGLN) |
| Broad commodities | Invesco Bloomberg Commodity UCITS ETF (GBP) | UNVERIFIED | CMOP, **pence** | UNVERIFIED | UNVERIFIED | UCITS (from name); replication UNVERIFIED | UNVERIFIED | [HL](https://hl.co.uk/shares/shares-search-results/i/invesco-bloomberg-commodity-ucits-etf-gbp) |
| Global property | iShares Developed Markets Property Yield UCITS ETF USD Dist | IE00B1FZS350 | IWDP, **pence** | Quarterly | 0.59 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:IWDP) |
| Benchmark: global equity | Vanguard FTSE All-World UCITS ETF | IE00B3RBWM25 | VWRL, £ | Quarterly | 0.14 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VWRL) |
| Benchmark: 60/40 | 60% VWRL / 40% VGOV, rebalanced monthly | — | — | — | — | — | — | Composition per research protocol §5 |

Notes:

- **Non-GBP lines are excluded.** Every candidate above is quoted in GBP or GBX on its London line. Some funds hold USD assets (CSP1, IWDP), which is currency exposure inside a GBP-quoted line, not FX conversion by the bot.
- **Distributing funds.** Total-return series must add back distributions (portfolio spec §2: `tr_close`). The data source must provide distribution history or adjusted prices.
- **Inception dates matter for the holdout.** Rows marked UNVERIFIED must be filled before Phase 1 fixes the holdout dates.

## Table C — Historical data options

| Source | Coverage | Total return or price only | Cost | Licence limits | Verdict |
|---|---|---|---|---|---|
| IBKR API historical bars | UNVERIFIED (D5) | UNVERIFIED | UNVERIFIED (may need a market-data subscription) | Personal use under the account agreement | First choice, if depth and adjustments are adequate. BLOCKED: account pending |
| Issuer factsheets and NAV history (Vanguard, iShares) | Fund life only | NAV and distributions, usually downloadable | Free | Issuer terms | Good for reconstructing total return and cross-checking prices (Gate 1 second source) |
| Free aggregators (e.g. Yahoo Finance) | Varies | Usually adjusted close | Free | Terms restrict automated and commercial use | Research comparison only, never authoritative |
| Index proxy history (e.g. FTSE, Bloomberg indices) | Decades | Index total return | Often licensed | Index-provider licences | Only where D2-style gaps exist, labelled as proxy, reported separately |

No purchase without owner approval (charter §5).

## Decisions requested from the owner

1. **D1 gold:** allow the physical gold ETC as the one non-UCITS exception, or drop gold.
2. **D2 US Treasuries:** proxy history, another line, or drop the role.
3. **D3:** approve the GBX → GBP normalisation rule for the data layer. This becomes a T-005 requirement.
4. **D4 and D5:** once the account is approved, read the LSE commission and test API historical bars. Then confirm or replace the £3 reserve.
5. **Data spend:** none proposed yet. Decide after D5, within the £600-a-year ceiling.
