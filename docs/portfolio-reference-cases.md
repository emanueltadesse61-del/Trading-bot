# Portfolio Reference Cases

Status: **Review — awaiting Codex acceptance (T-002).** Calculated independently by Claude from `docs/portfolio-spec.md`. Machine-readable values, including every intermediate step: `tests/fixtures/portfolio_cases.json` (absolute tolerance 1e-8).

Claude's calculator is deliberately **not** in the repository. Codex's implementation must reproduce these numbers on its own; a mismatch is investigated, not patched over (see `AGENTS.md`, disagreements).

Covariance in the weight cases = outer(vol_252d) × correlation; unlisted pairs have correlation 0.

## Weight cases

| Case | What it exercises | Key expected result |
|---|---|---|
| W1_asset_cap | 6 instruments, top-4 selection drops BD_GILT and BD_UST; GOLD capped | GOLD 0.25 (from 0.2595); EQ_US 0.2027; EQ_UK 0.1622; EQ_JP 0.1006; BD_UST 0.0729; cash 0.2117; σp 0.0933, no scaling |
| W2_class_cap | Equities 83.3% before caps | Each equity 0.2083 × 0.72 = 0.15; cash 0.40 |
| W3_all_cash | No positive trend, all momentum negative | Every weight 0; cash 1.0 |
| W4_vol_ceiling | Correlated high-vol holdings | σp 0.1676 → scale 0.5966; equities 0.1193 each, COM 0.1205; cash 0.5215. Class cap applies first (equities 0.6058 → 0.60) |
| W5_tie_negative_ineligible | F ineligible (σ 0.004); D/E tie for 4th, D wins by id; C, D in TopN with negative returns | A 0.1724 (= 0.5 × 10/29); B 0.0862 (= 0.5 × 5/29); cash 0.7414 |

### W1 by hand

1/σ: EQ_UK 5, EQ_US 6.25, EQ_JP 4, BD_GILT 12.5, BD_UST 10, GOLD 8; sum 45.75.

- Trend sleeve: EQ_UK 5/45.75 = 0.10929; EQ_US 0.13661; EQ_JP (⅓ × 4)/45.75 = 0.02914; BD_UST (⅔ × 10)/45.75 = 0.14572; GOLD 0.17486; BD_GILT 0.
- Momentum ranking: EQ_US 0.18, EQ_UK 0.12, GOLD 0.09, EQ_JP 0.05 | BD_UST 0.02, BD_GILT −0.04. Denominator 6.25 + 5 + 8 + 4 = 23.25.
- Momentum sleeve: EQ_US 0.26882, EQ_UK 0.21505, GOLD 0.34409, EQ_JP 0.17204.
- Combined: GOLD 0.5 × (0.17486 + 0.34409) = 0.25948 → capped at 0.25. Equity class 0.4655 < 0.60.

## Order cases

| Case | Setup | Expected orders |
|---|---|---|
| O1_band_exit_cap_cashlimit | W1 targets, NAV £10,000 (settled £1,300 + unsettled £1,000 + £7,700 holdings) | SELL BD_GILT 10 (exit, band); SELL GOLD 8 (asset_cap, band: 28% → floor(2500/40) = 62 shares); BUY EQ_JP 34; BUY EQ_US 8. Buys needed £1,507.50 with buffer > £1,300 settled, so k = 0.86235: EQ_JP floor(40k) = 34, EQ_US floor(10k) = 8. EQ_UK (16.0% vs 16.2%) and BD_UST (8.0% vs 7.3%) are inside the band: no trade |
| O2_post_trade_class_repair | W2 targets; EQ1–EQ3 at 16.9% (inside band), EQ4 at 9% | First pass buys EQ4 60 → equity class would be 65.7% → repair adds EQ1–EQ3. Final: SELL EQ1/EQ2/EQ3 19 each (repair_class), BUY EQ4 60 (band) |
| O3_blocked_open_orders | Open order present | BLOCKED_OPEN_ORDERS, no orders |
| O4_blocked_held_ineligible | F (ineligible) held | BLOCKED_HELD_INELIGIBLE, no orders |

## Signal case

S1_signals_from_prices gives explicit 253-value price arrays. Expected:

| Instrument | Eligible | Trend score | Momentum return | σ (60d, ann.) |
|---|---|---|---|---|
| UPTREND | yes | 1 | 0.08594 | 0.07855 |
| DOWNTREND | yes | 0 | −0.10738 | 0.11736 |
| MIXED | yes | ⅓ (R63 < 0, R126 > 0, R252 > 0) | 0.33684 | 0.10965 |
| FLAT | no (min_vol) | — | — | 0 |
| SHORT | no (insufficient_history, 200 closes) | — | — | — |

The fixture also gives the expected annualised covariance matrix of the three eligible instruments.

## Coverage against T-002 requirements

| Requirement | Case |
|---|---|
| Cash allocation | W3, W5, O1 (unsettled cash) |
| Asset cap | W1, O1 |
| Class cap, proportional reduction | W2, W4 |
| Volatility reduction | W4 |
| Actual-vs-target bands | O1, O2 |
| Rounding | O1, O2 |
| Settled-cash limit | O1 |
| Post-rounding constraint check | O2 |
| Top-4 selection with more than four assets | W1, W5 |
| Ties | W5 |
| Insufficient history, zero volatility | S1, W5 |
| Blocked states | O3, O4 |
