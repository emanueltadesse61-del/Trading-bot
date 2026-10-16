## T-010: Opening prices, distribution pay dates, raw-dataset schema v2 and `market_from_raw`

**State:** Review, v1. **Codex checks the requirements before building.**
**Phase:** 2   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** PR #15 (T-009 card) merged, since this branch is built on it; data spec v1.3, backtest spec v1.3 and decision 0011 (this PR). It can be built in parallel with the T-009 implementation: the two share no code.

### Goal
Stored real data can carry the two things the backtester needs that v1 lacks: **opening prices**, so fills happen at the next open, and **distribution pay dates**, so dividend cash arrives when it is actually paid. There is also one audited bridge from a stored dataset to the simulator. Real-data backtests stay refused until the Gate 3 statistics card.

### Inputs
- `docs/data-spec.md` v1.3 (§2.2, §8.4.1, §10), `docs/backtest-spec.md` v1.3 (§2.1.1, §2.2, §3 step 2), decision 0011
- `tests/fixtures/backtest_cases.json` v1.3: BT13 is new; every earlier case is unchanged
- `trader.data` (T-005–T-007), `trader.backtest` (T-008)

### Outputs
1. **Records:** `DistributionRecord.pay_date: date | None = None`. Existing callers are unchanged.
2. **CSV import v2** (data spec §8.4.1): version chosen by the `prices.csv` header; `distributions.csv` must match; `open` optional per row; `pay_date` required and ≥ `ex_date` (`IMPORT_PAY_BEFORE_EX`). The public `import_csv` and `trader-split` handle both versions; a v2 source produces v2 partitions.
3. **Raw-dataset schema v2:** `write_raw_dataset(…, schema="v1" | "v2")` with no default, plus `read_raw_dataset` for both schemas (data spec §8.4.1). v1 refuses `pay_date` (`PAY_DATES_UNSUPPORTED`) and opens, as now. v2 requires pay dates.
4. **Backtester:** pay-date settlement (backtest spec §3 step 2), the `BACKTEST_PAY_DATE` admission check, and `market_from_raw(raw_dataset, exceptions_snapshot)` (§2.1.1) with `BACKTEST_RAW_SCHEMA` for v1. The exceptions snapshot is the registry spec §5 format. If the registry's parser is not merged yet, implement the same strict parser in `trader.data` and let the registry reuse it; there must be no two parsers.
5. **README:** the CSV v2 format and the note that distribution history comes from issuer sources (decision 0011).

### Constraints
- Synthetic data only. No network, broker, real or holdout data.
- No change to `build_dataset`'s outputs or behaviour, the accepted fixtures' values (BT13 is added), or the registry's `SUPPORTED_REAL_SCHEMAS`, which stays empty.
- v1 datasets and their ids must still read back exactly as before.

### Acceptance criteria
- [ ] **Fixture:** every simulator case, including BT13, reproduces with the existing harness. BT13 needs pay dates passed through `DistributionRecord.pay_date`.
- [ ] **CSV v2:**
  - v2 headers parse, with an open empty or numeric;
  - a v1 `prices.csv` with a v2 `distributions.csv` (and the reverse) gives `IMPORT_BAD_HEADER`;
  - a missing `pay_date` gives `IMPORT_BAD_DATE`;
  - a `pay_date` before `ex_date` gives `IMPORT_PAY_BEFORE_EX`;
  - a non-numeric `open` gives `IMPORT_BAD_NUMBER`;
  - the leak rule still uses `date` and `ex_date` only: a development `pay_date` after the holdout start is accepted.
- [ ] **Schema v2:**
  - round trip is byte-identical twice, with ids differing from v1 for the same rows;
  - a v1 dataset written before this card still reads with the same `dataset_id`;
  - v2 without a pay date, v1 with a pay date, and v1 with an open are each refused with their codes;
  - tampering a v2 `open` byte is detected;
  - `trader-split` on a v2 source gives two v2 partitions whose events partition exactly.
- [ ] **Backtester:**
  - `market_from_raw` on v2 returns a market whose `run_backtest` result equals one built directly from the same records;
  - on v1 it gives `BACKTEST_RAW_SCHEMA`;
  - `BACKTEST_PAY_DATE` is raised;
  - a synthetic run without pay dates still uses `DISTRIBUTION_LAG`, with unchanged results.
- [ ] Existing tests are unchanged and pass. CI green; `docs/handoff.md` updated.

### Exclusions
The IBKR export tool (T-011), Gate 3 statistics and enabling real runs (later card), freezing H-001, real or holdout data, FX.
