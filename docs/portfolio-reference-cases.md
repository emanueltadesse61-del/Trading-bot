# Portfolio Reference Cases (spec v1.2)

Status: **Review — v1.2 awaiting Codex re-check (T-002).** Calculated independently by Claude from `docs/portfolio-spec.md` v1.2. Machine-readable values, with every intermediate step: `tests/fixtures/portfolio_cases.json` (absolute tolerance 1e-8). Changes from v1 are in `docs/decisions/0002-t002-review-resolutions.md` and `0003-portfolio-volatility-numerics.md`.

Claude's calculator is deliberately **not** in the repository. Codex's implementation must reproduce these numbers on its own. A mismatch is investigated, not patched over (`AGENTS.md`, disagreements).

Fixture conventions are listed in `meta.conventions`. In short: covariance = outer(vol_252d) × correlation, with unlisted pairs 0; `null` in a price series is a missing close; order cases take their targets, eligible set and covariance from the weight case named in `targets_from`.

## Weight cases

| Case | What it exercises | Key expected result |
|---|---|---|
| W1_asset_cap | 6 instruments; top-4 selection drops BD_GILT and BD_UST; GOLD capped | GOLD 0.25 (from 0.2595); EQ_US 0.2027; EQ_UK 0.1622; EQ_JP 0.1006; BD_UST 0.0729; cash 0.2117; σp 0.0933, no scaling |
| W2_class_cap | Equities 83.3% before caps | Each equity 0.2083 × 0.72 = 0.15; cash 0.40 |
| W3_all_cash | All eligible; no positive trend; all momentum negative | Every weight 0; cash 1.0 |
| W4_vol_ceiling | Correlated high-volatility holdings | Class cap first (equities 0.6058 → 0.60), then σp 0.1676 → scale 0.5966; equities 0.1193, COM 0.1205; cash 0.5215 |
| W5_tie_negative_ineligible | F ineligible (σ 0.004); D and E tie for 4th, D wins by id; C and D in TopN with negative returns | A 0.1724 (= 0.5 × 10/29); B 0.0862 (= 0.5 × 5/29); cash 0.7414 |
| W6_hedged_pair | X and Y, σ 50%, correlation −0.8 | Both capped at 0.25; σp 0.0791, no scaling; cash 0.50 |
| W7_empty_universe | Both instruments fail MIN_VOL | Eligible set empty; cash 1.0 |
| W8_negative_quadratic_boundary | Explicit Σ with smallest eigenvalue ≈ −5e-13 (valid); weights 0.25/0.25 give xᵀΣx ≈ −6.25e-14 | Clamped: σp = 0, scale 1, weights 0.25/0.25, cash 0.50 |

### W1 by hand

1/σ: EQ_UK 5, EQ_US 6.25, EQ_JP 4, BD_GILT 12.5, BD_UST 10, GOLD 8; sum 45.75.

- **Trend sleeve:** EQ_UK 5/45.75 = 0.10929; EQ_US 0.13661; EQ_JP (⅓ × 4)/45.75 = 0.02914; BD_UST (⅔ × 10)/45.75 = 0.14572; GOLD 0.17486; BD_GILT 0.
- **Momentum ranking:** EQ_US 0.18, EQ_UK 0.12, GOLD 0.09, EQ_JP 0.05 | BD_UST 0.02, BD_GILT −0.04. Denominator 6.25 + 5 + 8 + 4 = 23.25.
- **Momentum sleeve:** EQ_US 0.26882, EQ_UK 0.21505, GOLD 0.34409, EQ_JP 0.17204.
- **Combined:** GOLD 0.5 × (0.17486 + 0.34409) = 0.25948, capped at 0.25. Equity class 0.4655 < 0.60.

## Order cases

| Case | Setup | Expected |
|---|---|---|
| O1_band_exit_cap_cashlimit | W1 targets; NAV £10,000 (settled £1,300 + unsettled £1,000 + £7,700 holdings) | SELL BD_GILT 10 (band, exit); SELL GOLD 8 (asset_cap, band); BUY EQ_JP 34; BUY EQ_US 8. Buys £1,507.50 with buffer + 2 × £3 reserve = £1,513.50 > £1,300, so k = (1300 − 6)/1507.5 = 0.858375: EQ_JP floor(40k) = 34, EQ_US floor(10k) = 8. EQ_UK and BD_UST inside the band |
| O2_post_trade_class_repair | W2 targets; EQ1–EQ3 at 16.9%, EQ4 at 9% | First pass buys EQ4 60, so equities would reach 65.7%; repair adds EQ1–EQ3. Final: SELL EQ1/EQ2/EQ3 19 each (repair_class), BUY EQ4 60 (band). Buy need £606 |
| O3_blocked_open_orders | Open order present | BLOCKED_OPEN_ORDERS |
| O4_blocked_held_ineligible | F (ineligible) held | BLOCKED_HELD_INELIGIBLE |
| O5_zero_signal_exit | W3 (eligible, all targets 0); EQ1 and BD1 held | SELL BD1 50, SELL EQ1 100 (band, exit) |
| O6_empty_universe_nothing_held | W7; nothing held | OK, no orders |
| O7_empty_universe_held | W7; P held | BLOCKED_HELD_INELIGIBLE, not sold |
| O8_blocked_nav | Unfunded account | BLOCKED_NAV |
| O9_unresolved_vol | W6; X held at target; Y unbought; no settled cash | k = 0, so Y can't be bought; post-trade σ 12.5% > 10%; nothing new to repair → BLOCKED_CONSTRAINTS |
| O10_unknown_holding | ZZZ held, not in the universe | BLOCKED_UNKNOWN_HOLDING |

## Signal case

S1_signals_from_prices: 253 weekday sessions from 2025-01-01, one value per session per series.

| Instrument | Eligible | Reason / trend score | Momentum return | σ (60d, ann.) |
|---|---|---|---|---|
| UPTREND | yes | trend 1 | 0.08594 | 0.07855 |
| DOWNTREND | yes | trend 0 | −0.10738 | 0.11736 |
| MIXED | yes | trend ⅓ (R63 < 0, R126 > 0, R252 > 0) | 0.33684 | 0.10965 |
| FLAT | no | min_vol | — | 0 |
| SHORT | no | insufficient_history (first 53 sessions missing) | — | — |
| STALE | no | missing_data (no close at t) | — | — |
| GAP | no | missing_data (one session missing mid-window) | — | — |

The fixture also gives the annualised covariance matrix of UPTREND, DOWNTREND and MIXED.

## Invalid-input cases

| Case | Stage | Input | Expected error |
|---|---|---|---|
| V1_nan_sigma | targets | σ(EQ_US) = NaN | INVALID_SIGMA |
| V2_asymmetric_covariance | targets | One entry off by 1e-6 | INVALID_COVARIANCE |
| V3_unknown_asset_class | targets | GOLD class "crypto" | INVALID_ASSET_CLASS |
| V4_zero_price | plan | Held EQ_UK price 0 | INVALID_PRICE |
| V5_fractional_holding | plan | 1.5 shares | INVALID_HOLDING |
| V6_negative_cash | plan | Settled cash −1 | INVALID_CASH |
| V7_duplicate_date | signals | Last date duplicated | INVALID_CALENDAR |
| V8_negative_price | signals | Close at t = −1 | INVALID_PRICE_SERIES |
| V9_eigenvalue_below_tolerance | targets | W8 with smallest eigenvalue ≈ −1e-11 | INVALID_COVARIANCE |

## Coverage

| Requirement | Cases |
|---|---|
| Cash allocation | W3, W5, W7, O1 |
| Asset cap / class cap (proportional) | W1, O1 / W2, W4 |
| Volatility reduction / unresolved volatility / negative-rounding boundary | W4 / O9 / W8, V9 |
| Actual-vs-target bands, rounding | O1, O2 |
| Settled cash with commission reserve | O1, O9 |
| Post-rounding constraint check | O2, O9 |
| Top-4 selection with more than four assets; ties | W1, W5 |
| Insufficient history, missing sessions, stale close, zero volatility | S1, W5, W7 |
| Every BLOCKED status in spec §7 | O3, O4, O7, O8, O9, O10 |
| Invalid inputs | V1–V9 |
