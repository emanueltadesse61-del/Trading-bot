# Feasibility Matrix (T-004)

Status: **Draft v2 — Review (Claude under decision 0004; revised for Codex findings F1, F2 on 8aa48b9).** Public facts checked 2026-10-16. Account checks: the owner reports the IBKR account **approved 2026-10-16**; the account checks below are **pending with the owner** and none is verified here.

Cell values follow the T-004 rule. A cell holds a value with its source, `UNVERIFIED`, or `BLOCKED: <reason>`. **No check is recorded as passed without a source.** Nothing here has been verified inside the owner's account.

## Summary: findings that need owner decisions

| # | Finding | Why it matters | Options | Cost |
|---|---|---|---|---|
| D1 | The GBP gold candidate (iShares Physical Gold, SGLN) is an **ETC, not a UCITS fund**. AJ Bell lists it as "UCITS: No" | The charter universe is UCITS ETFs; an ETC has a different legal structure and issuer exposure, and may count as a complex product for the appropriateness test | (a) Allow a physical gold ETC as the one non-UCITS exception; (b) drop gold from v1 | None |
| D2 | The GBP-hedged US Treasury candidate (Vanguard VDTS) only launched **8 Feb 2022** | About 4.7 years of real history: too short for the development and holdout periods without index proxy data | (a) Use the index as proxy history (reported separately, per research protocol §3); (b) use an unhedged or older Treasury line; (c) drop the role | Possibly index data |
| D3 | Broker pages show some lines in **pence (GBX)** and others in **pounds (GBP)** | A price unit is a property of the **data feed**, not of the fund: the same line can come in GBX from one source and GBP from another. Mixing them puts prices out by 100× | Data-layer rule: read the unit from the chosen feed's metadata for each instrument, convert to GBP, record the original unit. Never infer the unit from the fund name or a broker web page | None |
| D4 | IBKR's public UK table: **Fixed (IB SmartRouting) 0.05% of trade value, minimum £3.00 per order**, third-party fees shown as none; Fixed direct routing 0.10%, minimum £4.00; Tiered from 0.05%, minimum £1.00 plus third-party fees ([IBKR](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php), checked 2026-10-16) | `COMMISSION_RESERVE` covers **buys only** (portfolio spec §6.3 step 5). A buy cannot exceed its target, which is at most 25% of NAV, so at a £10,000 NAV a buy is at most £2,500 and its commission is the £3 minimum (0.05% × £2,500 = £1.25). That matches the reserve. Two limits to this: (1) **sales are not capped by the 25% target**, because exits and drifted holdings can be sold in one order. Codex's example: a £7,000 sale costs 0.05% × £7,000 = £3.50. Sale proceeds do **not** always cover the sale's own commission: Codex's example is a £1 exit, where the £3 minimum leaves a £2 shortfall. The planner reserves commission for buys only, so **fees on sales are not reserved**. Requirement for Phase 4: before any order is submitted, the risk gate must verify that settled cash remains ≥ 0 after **all** commissions in the run (sales and buys) at fresh prices and the account's actual fee schedule, and must block or trim the plan otherwise. The backtest cost model must charge the real commission on every order, including the minimum on small sales. (2) A buy's commission exceeds £3 once 0.05% × 25% × NAV > £3, i.e. above a NAV of £24,000, so the reserve must be revisited before the account grows past that | Owner confirms the actual plan (Fixed or Tiered), routing and any entitlements in the account; these stay BLOCKED | None |
| D5 | Paper accounts show **delayed** data for unsubscribed products, and real-time data needs an approved, funded account | Weekly decisions on daily closes don't need real-time data, but the historical-bar depth and cost via the API are unknown | Check API historical bars on the paper account; decide on a paid source only if it falls short | Possibly within the £600/yr ceiling |

## Table A — Account checks (owner performs)

| Check | Evidence needed | Status | Public notes |
|---|---|---|---|
| IBKR UK account approved; cash account (no margin) | Account settings or statement | Owner-reported: approved 2026-10-16. Cash-account (no margin) status UNVERIFIED | — |
| Paper account available and linked | Paper login works | Owner-reported 2026-10-16: paper login works on IB Gateway. Not independently verified | — |
| Permissions: LSE-listed UCITS ETFs (and an ETC, if D1(a)) | Permissions page. Note: options and other complex products are **not** needed | PENDING: owner check. D1(a) chosen, so the SGLN ETC permission must be confirmed | — |
| API access enabled for paper | Successful connection from a test script on the owner's machine, not an agent workspace | Owner-reported 2026-10-16: read-only IB Gateway connection (port 4002) from the owner's machine succeeded. Not independently verified | — |
| IB Gateway login method and re-authentication frequency | Owner observation over 2 weeks | PENDING: owner observation | UNVERIFIED |
| Market data: free, delayed or subscription for LSE ETFs; monthly cost | Market data page and account entitlements | PENDING: owner check. Entitlements UNVERIFIED | Unsubscribed paper data is delayed; real-time subscriptions need an approved, fully funded account ([IBKR](https://www.interactivebrokers.com/en/trading/papertrader-delayed-data.php)) |
| Historical daily bars via API: depth per instrument, pacing limits | Test request results | Owner-reported partial 2026-10-16: VWRP and IGLT returned daily bars, unsubscribed. These are **not** the configured lines; depth for the 11 data instruments and pacing are UNVERIFIED | UNVERIFIED |
| Commission plan, routing and entitlements actually applied to the account | Account pricing settings, with date | PENDING: owner check | Public UK schedule recorded in D4; the account's plan is not yet known |
| Can unsettled sale proceeds fund buys in a cash account? | IBKR documentation | UNVERIFIED | The spec does not use them either way (portfolio spec §6.3 step 5) |
| Withdrawals can be disabled for the API user | IBKR documentation or settings | UNVERIFIED | — |
| UK stamp duty on ETF purchases | HMRC or broker statement | UNVERIFIED | Commonly reported as not charged on ETFs; confirm before setting the cost model |

## Table B — Instrument matrix (candidates, not decisions)

Fields come from issuer or broker pages fetched on 2026-10-16. "Charge" is the ongoing charge as displayed; AJ Bell shows it without a unit, and it is read as % a year. **Available in account** is PENDING the owner's checks for every row.

| Role | Candidate | ISIN | LSE ticker and unit shown on source page | Income | Charge | Structure | Share-class inception | Source |
|---|---|---|---|---|---|---|---|---|
| UK equity | Vanguard FTSE 100 UCITS ETF (GBP) Distributing | IE00B810Q511 | VUKE, GBP (NAV in GBP) | Distributing, quarterly | 0.09% | Irish UCITS | 22 May 2012 | [Vanguard](https://www.vanguard.co.uk/professional/product/etf/equity/9509/IE00B810Q511) |
| US equity | iShares Core S&P 500 UCITS ETF USD (Acc) | IE00B5BMR087 | CSP1, **pence** | Accumulating | 0.07 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:CSP1) |
| Europe ex-UK equity | Vanguard FTSE Developed Europe ex UK UCITS ETF | IE00BKX55S42 | VERX, £ | Quarterly | 0.1 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE%3AVERX) |
| Japan equity | Vanguard FTSE Japan UCITS ETF | IE00B95PGT31 | VJPN, £ | Quarterly | 0.1 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VJPN) |
| Emerging-markets equity | Vanguard FTSE Emerging Markets UCITS ETF | IE00B3VVMM84 | VFEM, £ | Quarterly | 0.17 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VFEM) |
| UK gilts | Vanguard U.K. Gilt UCITS ETF | IE00B42WWV65 | VGOV, £ | Monthly | 0.05 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VGOV) |
| ~~US Treasuries, GBP-hedged~~ **DROPPED for v1 (decision 0008)** | Vanguard USD Treasury Bond UCITS ETF GBP Hedged Distributing | IE000S0PSP47 | VDTS, GBP | Distributing, monthly | 0.08% | Irish UCITS | **08 Feb 2022** (D2) | [Vanguard](https://www.vanguard.co.uk/professional/product/etf/bond/E024/usd-treasury-bond-ucits-etf-gbp-hedged-distributing) |
| Inflation-linked bonds | iShares £ Index-Linked Gilts UCITS ETF GBP (Dist) | IE00B1FZSD53 | INXG, £ | Semi-annual | 0.1 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:INXG) |
| Gold | iShares Physical Gold ETC | IE00B4ND3602 | SGLN, **pence** | None | 0.12 | **ETC, "UCITS: No"** (D1) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:SGLN) |
| Broad commodities | Invesco Bloomberg Commodity UCITS ETF (GBP) | UNVERIFIED | CMOP, **pence** | UNVERIFIED | UNVERIFIED | UCITS (from name); replication UNVERIFIED | UNVERIFIED | [HL](https://hl.co.uk/shares/shares-search-results/i/invesco-bloomberg-commodity-ucits-etf-gbp) |
| Global property | iShares Developed Markets Property Yield UCITS ETF USD Dist | IE00B1FZS350 | IWDP, **pence** | Quarterly | 0.59 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:IWDP) |
| Benchmark: global equity | Vanguard FTSE All-World UCITS ETF | IE00B3RBWM25 | VWRL, £ | Quarterly | 0.14 | UCITS (from name) | UNVERIFIED | [AJ Bell](https://www.ajbell.co.uk/market-research/LSE:VWRL) |
| Benchmark: 60/40 | 60% VWRL / 40% VGOV, rebalanced monthly | — | — | — | — | — | — | Composition per research protocol §5 |

### Table B2 — Phase 1 checklist per candidate (required by T-004)

Share-class inception is **not** evidence of usable price history. History coverage is recorded separately and must be shown from the chosen feed.

| Role | Ticker | Currency hedging | KID available | Typical spread source | Available in account | History source and first usable date |
|---|---|---|---|---|---|---|
| UK equity | VUKE | None stated on source page — UNVERIFIED | UNVERIFIED | UNVERIFIED (measure from feed in Phase 1) | PENDING: owner check | UNVERIFIED |
| US equity | CSP1 | None stated ("USD" share class name) — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Europe ex-UK equity | VERX | None stated — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Japan equity | VJPN | None stated — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Emerging-markets equity | VFEM | None stated — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| UK gilts | VGOV | Not applicable (GBP assets) — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| ~~US Treasuries, GBP-hedged~~ **DROPPED (0008)** | VDTS | GBP hedged (fund name, [Vanguard](https://www.vanguard.co.uk/professional/product/etf/bond/E024/usd-treasury-bond-ucits-etf-gbp-hedged-distributing)); method UNVERIFIED | UNVERIFIED | UNVERIFIED | BLOCKED: account pending | UNVERIFIED; cannot predate 08 Feb 2022 without proxy (D2) |
| Inflation-linked bonds | INXG | Not applicable (GBP assets) — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Gold | SGLN | None stated — UNVERIFIED | UNVERIFIED (ETC; KID requirement may differ, D1) | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Broad commodities | CMOP | UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Global property | IWDP | None stated — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |
| Benchmark: global equity | VWRL | None stated — UNVERIFIED | UNVERIFIED | UNVERIFIED | PENDING: owner check | UNVERIFIED |

Every UNVERIFIED cell must hold a sourced value before Phase 1 fixes the holdout dates.

Notes:

- **Non-GBP lines are excluded.** Every candidate above is quoted in GBP or GBX on its London line. Some funds hold USD assets (CSP1, IWDP), which is currency exposure inside a GBP-quoted line, not FX conversion by the bot.
- **Distributing funds.** Total-return series must add back distributions (portfolio spec §2: `tr_close`). The data source must provide distribution history or adjusted prices.
- **Units on source pages are display units**, not feed units (D3).

## Table C — Historical data options

None of the access, adjustment, cost or licence properties below has been verified. Each cell states what is unknown and the evidence needed.

| Source | Coverage | Total return or price only | Cost | Licence and automation limits | Evidence needed | Verdict |
|---|---|---|---|---|---|---|
| IBKR API historical bars | UNVERIFIED (D5) | UNVERIFIED | UNVERIFIED: may need a market-data subscription | UNVERIFIED | Test requests on the paper account; IBKR market-data and API terms, dated | Preferred candidate if depth and adjustments suffice. PENDING: owner's full-history check (partial owner-reported probe under D5) |
| Issuer NAV and distribution history (Vanguard, iShares) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Locate the download for one fund; read the issuer site's terms of use, dated | Candidate second source for Gate 1 cross-checks |
| Free aggregators (e.g. Yahoo Finance) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | The provider's terms of service, dated | Research comparison only, never authoritative, until terms are checked |
| Index proxy history (e.g. FTSE, Bloomberg indices) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | Index-provider licence and data terms, dated | Only where D2-style gaps exist, labelled as proxy, reported separately |

No purchase without owner approval (charter §5).

## Decisions requested from the owner

1. **D1 gold:** **Decided 2026-10-16 — (a)**: SGLN is the one named non-UCITS exception, if the account can trade it (decision 0008).
2. **D2 US Treasuries:** **Decided 2026-10-16 — (c)**: dropped for v1; no GBP-hedged line has ≈ 8 years of history (VDTS 2022, GOVP 2019, IGTM 2019) (decision 0008).
3. **D3:** approve the GBX → GBP normalisation rule for the data layer. This becomes a T-005 requirement.
4. **D4 and D5:** the public UK schedule supports the £3 reserve (D4). Once the account is approved, confirm the plan and routing actually applied, and test API historical bars. **Owner-reported 2026-10-16:** on the unfunded account's paper login, IB Gateway read-only API returned daily bars for VWRP (data from 2019-07-25) and IGLT (from 2006-12-04), 253 bars over the last year, with no subscription. Still to check: full depth for all 11 instruments, units, split adjustment of `TRADES` bars, distribution history.
5. **Data spend:** none proposed yet. Decide after D5, within the £600-a-year ceiling.
