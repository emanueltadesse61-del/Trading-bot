# 0011 — Opening prices, distribution pay dates and raw-dataset schema v2 (T-010)

Date: 2026-10-16. Status: **Proposed by Claude**; Codex checks before building; the owner merges. Applies to data spec v1.3 (§2.2, §8.4.1, §10), backtest spec v1.3 (§2.1.1, §3 step 2) and `tests/fixtures/backtest_cases.json` v1.3 (BT13).

| # | Choice | Why | Alternative considered |
|---|---|---|---|
| 1 | **A new schema version (v2)** instead of changing v1 in place | Accepted v1 datasets and their ids stay valid and readable; v2 ids can't collide (the schema string is in the identity) | Mutate v1: silently changes the meaning of pinned ids |
| 2 | **`open` nullable; `pay_date` required in v2** | A missing open only cancels that session's order (backtest spec §4). A missing pay date would force the unverified `DISTRIBUTION_LAG` assumption that decision 0009 row 5 says needs evidence | Optional pay dates: lets the assumption back in unnoticed |
| 3 | **Distribution cash settles at the first session after the ex-date that is on or after the pay date** | It can't be spent before it is paid, nor on the ex-date itself (lag ≥ 1, decision 0010 row 18). Non-session pay dates move to the next session | Settle on the pay date's calendar day: undefined on weekends and holidays |
| 4 | **Pay dates are event attributes, not partitioned** | They are announced with the distribution, before the ex-date; a pay date after the holdout start reveals no later price | Partition by pay date: would split one distribution's facts across two datasets |
| 5 | **`market_from_raw` is the only bridge and accepts v2 only**; the registry still refuses real runs until the Gate 3 statistics card | The full evaluation (statistics included) should be in place before any real-data result is produced (protocol: freeze before Phase 3) | Enable real runs now: results would be seen before their judging statistics exist |
| 6 | **CSV v2 is chosen by the `prices.csv` header and must match `distributions.csv`** | One unambiguous version per import | Per-file versions: mixed v1 and v2 data |
| 7 | **H-001's `DISTRIBUTION_LAG` is still required when frozen but has no effect on v2 data** | The registry's completeness rule is unchanged; the freezing decision records it as an unused fallback | Remove the parameter: changes the accepted T-008 interface |

Distribution history (ex-dates, pay dates, amounts) is **not** expected from IBKR's price bars. It comes from issuer distribution histories, prepared by the owner with sources as declaration evidence (data spec §8.5). The owner-run IBKR price export is a separate card (T-011).
