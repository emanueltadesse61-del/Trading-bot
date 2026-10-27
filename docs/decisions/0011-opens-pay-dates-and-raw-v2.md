# 0011 — Opening prices, distribution pay dates and raw-dataset schema v2 (T-010)

Date: 2026-10-16. Status: **Proposed by Claude**; Codex checks before building; the owner merges. Applies to data spec v1.3 (§2.2, §8.4.1, §10), backtest spec v1.3 (§2.1, §2.1.1, §3 step 2, §12) and `tests/fixtures/backtest_cases.json` v1.3 (BT13). Rows 3 and 5 amended and rows 8–11 added after Codex's review (see the end).

| # | Choice | Why | Alternative considered |
|---|---|---|---|
| 1 | **A new schema version (v2)** instead of changing v1 in place | Accepted v1 datasets and their ids stay valid and readable; v2 ids can't collide (the schema string is in the identity) | Mutate v1: silently changes the meaning of pinned ids |
| 2 | **`open` nullable; `pay_date` required in v2** | A missing open only cancels that session's order (backtest spec §4). A missing pay date would force the unverified `DISTRIBUTION_LAG` assumption that decision 0009 row 5 says needs evidence | Optional pay dates: lets the assumption back in unnoticed |
| 3 | **Distribution cash settles at the first session after the ex-date that is on or after the pay date** | It can't be spent before it is paid, nor on the ex-date itself (lags ≥ 1, decision 0009 row 18). Non-session pay dates move to the next session. This is a **declared model**: whether cash is spendable at the pay-date open is unproven (row 9) | Settle on the pay date's calendar day: undefined on weekends and holidays |
| 4 | **Pay dates are event attributes, not partitioned** | They are announced with the distribution, before the ex-date; a pay date after the holdout start reveals no later price | Partition by pay date: would split one distribution's facts across two datasets |
| 5 | **`market_from_raw(dataset_dir, exceptions, exceptions_version)` is the only bridge; it reads and validates the dataset itself and accepts v2 only**; the registry still refuses real runs until the Gate 3 statistics card | The full evaluation (statistics included) should be in place before any real-data result is produced (protocol: freeze before Phase 3) | Enable real runs now: results would be seen before their judging statistics exist |
| 6 | **CSV v2 is chosen by the `prices.csv` header and must match `distributions.csv`** | One unambiguous version per import | Per-file versions: mixed v1 and v2 data |
| 7 | **H-001's `DISTRIBUTION_LAG` is still required when frozen but has no effect on v2 data** | The registry's completeness rule is unchanged; the freezing decision records it as an unused fallback | Remove the parameter: changes the accepted T-008 interface |
| 8 | **The schema version travels explicitly**: CSV header → parser result → split partitions → validated manifest → the bridge, which reads the directory itself | A v2 dataset with no opens or distributions is record-identical to v1, so the version can't be inferred, and a caller's label can't be trusted (Codex B1) | Infer from non-`None` fields: wrong for empty data |
| 9 | **Pay-date settlement is a declared model.** Real activation requires (a) evidence of IBKR's dividend cash timing, or an owner-approved convention plus a sensitivity run, and (b) evidence that pay dates are as announced on or before ex-date, or a gate on revised dates | A date-only field can't show cash was spendable at that morning's open, nor that it was known in advance (Codex B2) | Treat it as a guarantee: unproven |
| 10 | **`write_raw_dataset(..., schema="v1")` defaults to v1**; an unknown schema gives `SCHEMA_UNSUPPORTED`; mechanical updates to test **helpers** (CSV exporters that use `asdict`, which now meets `pay_date = None`) are authorised, with every prior assertion and fixture answer unchanged | Compatibility with all accepted callers and v1 bytes (Codex N1) | No default: breaks every existing call |
| 11 | **No exceptions-file parser in T-010**: the bridge takes parsed entries; the registry (T-009) owns the file format and parser | Removes the shared-code conflict between the parallel builds (Codex N4) | Move the parser into `trader.data`: couples the two builds |

## Re-review (Codex at `d739684`, record `101ea84`)

Codex reproduced BT13 and every earlier fixture section, then raised:
- **B1:** schema identity couldn't be determined from the bridge's input. Resolved by row 8 and data spec §8.4.1.
- **B2:** pay-date timing and point-in-time evidence were unproven. Resolved by row 9 and backtest spec §3 step 2 and §12.

Notes:
- **N1:** resolved by row 10.
- **N2:** stale wording in backtest spec §2.1 and registry spec §5.4, and this row 3's reference, all fixed.
- **N3:** `BACKTEST_PAY_DATE` covers wrong types; the v2 writer gives `PAY_DATE_INVALID`; admission scope stated.
- **N4:** resolved by row 11.

Distribution history (ex-dates, pay dates, amounts) is **not** expected from IBKR's price bars. It comes from issuer distribution histories, prepared by the owner with sources as declaration evidence (data spec §8.5). The owner-run IBKR price export is a separate card (T-011).
