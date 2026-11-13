# Proposal — Growth pivot: aim to beat global equity, not 60/40

Status: **DRAFT for the owner. Nothing here is decided.** Author: Claude. Date: 2026-10-16. Prepared at the owner's request ("how can we pivot in order to maximise profit, using the work already done"). It takes effect only through an owner decision record. That decision must be made **before any backtest on real data**; none exists yet, H-001 is still a draft, and no trial has been registered, so the pivot costs **0 of the 20 trials**.

## 1. The trade-off, stated plainly

Higher expected profit comes only from taking more risk; no strategy removes that. The pivot keeps the tested engine and changes its **goal and risk budget**:
- **Before:** returns similar to 60/40 with smaller falls (10% volatility ceiling).
- **After:** returns at least those of 100% global equity (VWRL), with falls no worse than VWRL's, at roughly equity-level risk.

The bot's possible advantage over simply holding VWRL is the trend signal moving out of equities during long declines, plus momentum tilting towards the strongest markets. The realistic hope is index-like or somewhat better long-run growth, not a multiple of it (R-007: published results decay).

## 2. What is reused unchanged

Data layer (T-005–T-007), holdout split, backtester and cost model (T-008), experiment registry (T-009), and the signal, target and planner code (T-002–T-003). The `global_equity` (VWRL) baseline already exists. **Only parameters, the universe, the charter and the Gate 3 rule change.**

## 3. Proposed changes

### 3.1 Charter §6 (amendment text, draft)

| Item | Now | Proposed |
|---|---|---|
| Primary objective | Gate 3 against 60/40 | Gate 3 against **100% global equity (VWRL)**, as amended in §3.2 |
| Deciding benchmark | 60/40 | **VWRL**, monthly band rebalancing (backtest spec §6.3). 60/40 is still reported |
| Strategy universe | 10 instruments | **13**: the 10, plus 3 equity funds (§3.4) |
| Rebalancing | Weekly primary | **Monthly primary**, to cut the £3-minimum drag; weekly as a robustness variant |

### 3.2 Research protocol §6 (draft): Gate 3 against VWRL

Paired monthly returns over the walk-forward period, as now. Outcomes in order:

| Step | Condition | Outcome |
|---|---|---|
| 1 | **Hard fail** if any: annualised return ≤ VWRL's; max drawdown worse than VWRL's; ΔSR (vs VWRL) ≤ 0; annualised return ≤ VWRL's at 2× costs (both sides); Sharpe less than the 10-month moving-average rule's + 0.10 | Fail |
| 2 | **Soft shortfall:** return advantage < 1.0 percentage point a year, or a positive advantage in < 80% of bootstrap paths | Inconclusive |
| 3 | One holdout evaluation by the owner: holdout return ≤ VWRL's, or a worse drawdown | Fail |
| 4 | Otherwise | Pass (paper trading only) |

**Honest caveat:** a return advantage is statistically noisier than a Sharpe advantage. With about 4 years of evaluable development history, only a large edge will clear step 2, so "Inconclusive" is a likely outcome even if a modest edge exists.

### 3.3 Strategy parameters (H-001 rewritten as the growth version; still a draft)

| Parameter | Now | Proposed | Why |
|---|---|---|---|
| `VOL_CEILING` | 0.10 | **0.16** | About global equity's long-run volatility; the cap still bites in turbulent markets |
| `CLASS_CAP` | 0.60 | **0.90** | Lets the portfolio be almost fully in equities when trends support it |
| `ASSET_CAP` | 0.25 | **0.30** | Allows more concentration in the strongest trend; still at least 4 holdings when fully invested |
| `TOP_N` | 4 | 4 | Unchanged |
| Trend lookbacks | 63/126/252 | 63/126/252 | Unchanged |
| Primary schedule | weekly | **monthly** | Cost drag at a small account size |

**Variants** (3 of 20 trials, as before):
- **V1** primary: monthly, as above;
- **V2** robustness: weekly;
- **V3** robustness: lookbacks 21/63/252.

V1 is the only one that can pass (decision 0010 rule).

### 3.4 Universe additions (candidates; checks pending)

| Role | Candidate | Ticker, line | Share-class history | Source | Still to check |
|---|---|---|---|---|---|
| US large-cap tech | Invesco EQQQ Nasdaq-100 UCITS ETF (Dist) | EQQQ, **pence (GBX)** | Since 2 Dec 2002 | [AJ Bell](https://www.ajbell.co.uk/market-research/sub/LSE:EQQQ/fund-info) | ISIN, charge, distribution history, IBKR availability |
| UK mid-cap | Vanguard FTSE 250 UCITS ETF (GBP) Dist | VMID, GBP | Since 30 Sep 2014; ISIN IE00BKX55Q28; 0.10%; quarterly | [Vanguard](https://www.vanguard.co.uk/professional/product/etf/equity/9525/ftse-250-ucits-etf-gbp-distributing) | IBKR availability |
| Global momentum | iShares Edge MSCI World Momentum Factor UCITS ETF (Acc) | IWFM, GBP line (pounds or pence unconfirmed) | Since 6 Oct 2014; ISIN IE00BP3QZ825; 0.25% | [BlackRock](https://www.blackrock.com/uk/individual/products/270051/ishares-msci-world-momentum-factor-ucits-etf) | Feed unit; IBKR availability; overlap with our own momentum sleeve |

All three pass the ≈ 8-year screen on inception date. Eligibility is still the actual valid-close count (decision 0008). The data instruments become 14: 13 strategy funds plus VWRL.

### 3.5 Paper-trading limits (charter §4): owner choice needed

The current pause at −15% and stop at −25% suit a 60/40-risk portfolio. At equity-level risk, falls of 20–30% are normal in bad years; the paper experiment would likely stop on ordinary volatility. Options:
- (a) keep −15% / −25% (strict; likely early stops);
- (b) **−20% / −35%**, roughly VWRL-like stress;
- (c) tie the limits to VWRL's own drawdown over the same period.

This is a risk-tolerance decision for the owner.

## 4. What does not change

No leverage, shorting, margin or leveraged ETFs. No LLM signals. Paper first, with real money only by a separate signed charter section. Trial history is never reset. The one-use holdout and the 8 March 2027 checkpoint stay.

## 5. Owner decisions requested

1. Adopt the growth objective and VWRL as the deciding benchmark (§3.1–3.2)?
2. Parameter changes (§3.3)?
3. Add EQQQ, VMID and IWFM, subject to the IBKR checks (§3.4)?
4. Paper-trading limits (§3.5): (a), (b) or (c)?

Once decided, Claude writes the decision record, the charter and protocol amendments, and the growth version of H-001 (still a draft until frozen from evidence). Codex checks them before anything runs.

*Not financial advice; illustrations from published research and fund pages fetched 2026-10-16.*
