## T-010: Opening prices, distribution pay dates, raw-dataset schema v2 and `market_from_raw`

**State:** Review, v2 (Codex findings B1–B2 and N1–N4 resolved; decision 0011 re-review section). **Codex re-checks before building.**
**Phase:** 2   **Author:** Claude   **Implementer:** Codex   **Reviewer:** Claude
**Depends on:** PR #15 (T-009 card) merged, since this branch is built on it; data spec v1.3, backtest spec v1.3 and decision 0011 (this PR). It shares no new code with the T-009 implementation (decision 0011 row 11), so the two can be built in parallel.

### Goal
Stored real data can carry **opening prices**, so fills happen at the next open, and **distribution pay dates**, so dividend cash arrives when it is paid, under a declared model. There is one audited bridge from a stored dataset to the simulator, with the schema version carried explicitly. Real-data backtests stay refused until the Gate 3 statistics card, after the activation prerequisites of backtest spec §12.

### Inputs
- `docs/data-spec.md` v1.3 (§2.2, §8.4.1, §10), `docs/backtest-spec.md` v1.3 (§2.1, §2.1.1, §2.2, §3 step 2, §12), decision 0011
- `tests/fixtures/backtest_cases.json` v1.3: BT13 under `pay_date_cases`; every earlier section unchanged
- `trader.data` (T-005–T-007), `trader.backtest` (T-008)

### Outputs
1. **Records:** `DistributionRecord.pay_date: date | None = None`.
2. **CSV import v2** (data spec §8.4.1):
   - the version is chosen by the `prices.csv` header, and `distributions.csv` must match;
   - `open` is optional per row; `pay_date` is required and ≥ `ex_date` (`IMPORT_PAY_BEFORE_EX`);
   - the private parser returns the parsed records **and** the CSV version;
   - `trader-split` writes both partitions with that version;
   - the public `import_csv` keeps its signature and return type.
3. **Raw-dataset schema v2:**
   - `write_raw_dataset(…, schema="v1")` keeps its default; `"v2"` is new; anything else gives `SCHEMA_UNSUPPORTED`;
   - v1 refuses opens (`OPEN_PRICES_UNSUPPORTED`) and pay dates (`PAY_DATES_UNSUPPORTED`);
   - v2 gives `PAY_DATE_INVALID` for a missing, wrongly typed or pre-ex-date pay date;
   - `read_raw_dataset` reads both schemas and validates v2 pay dates.
4. **Backtester:**
   - pay-date settlement (backtest spec §3 step 2);
   - `BACKTEST_PAY_DATE` (wrong type, or before the ex-date; in-scope records only);
   - `market_from_raw(dataset_dir, exceptions, exceptions_version)` (§2.1.1): reads and validates the directory itself, gives `BACKTEST_RAW_SCHEMA` for v1, defines no file parser.
5. **README:**
   - the CSV v2 format;
   - distribution history comes from issuer sources;
   - pay-date settlement is a declared model with real-data prerequisites (backtest spec §12).

### Constraints
- Synthetic data only. No network, broker, real or holdout data.
- `build_dataset` is unchanged; accepted fixture values are unchanged; `SUPPORTED_REAL_SCHEMAS` stays empty.
- v1 datasets and their ids read back exactly as before, and v1 writes are byte-identical to before.
- **Test migration (decision 0011 row 10):** mechanical updates to test **helpers** are allowed, e.g. CSV exporters that build rows with `asdict` must drop the new `None`-valued `pay_date`. No prior assertion, expected value or fixture answer may change.

### Acceptance criteria
- [ ] **Fixture:** every `simulator_cases` entry still reproduces. Each `pay_date_cases` entry (BT13) reproduces with the same harness, extended to pass `pay_date`.
- [ ] **Schema identity (B1):**
  - a v2 CSV source with **no distributions and every open empty** splits into two **v2** partitions (manifest schema v2), and `market_from_raw` accepts them;
  - the equivalent v1 source gives v1 partitions, which `market_from_raw` refuses (`BACKTEST_RAW_SCHEMA`);
  - a v1 dataset written before this card keeps its `dataset_id` and bytes;
  - `market_from_raw` has no schema argument.
- [ ] **CSV v2:**
  - v2 headers parse, with an open empty or numeric;
  - mixed v1/v2 headers give `IMPORT_BAD_HEADER`;
  - a missing `pay_date` gives `IMPORT_BAD_DATE`;
  - a pre-ex-date `pay_date` gives `IMPORT_PAY_BEFORE_EX`;
  - a non-numeric `open` gives `IMPORT_BAD_NUMBER`;
  - a development `pay_date` after the holdout start is accepted.
- [ ] **Schema v2 storage:**
  - two writes are byte-identical, and ids differ from v1 for the same rows;
  - `SCHEMA_UNSUPPORTED` for `schema="v3"`;
  - `PAY_DATE_INVALID` for missing, `datetime`-typed and pre-ex-date pay dates;
  - v1 with a pay date, and v1 with an open, are refused;
  - a tampered v2 `open` byte is detected;
  - a v2 split's events partition exactly.
- [ ] **Backtester:**
  - `market_from_raw` on v2 gives a run equal to one built directly from the same records;
  - `BACKTEST_PAY_DATE` for a string pay date, a `datetime` pay date, and a pay date before its ex-date, each on a run instrument dated ≤ `end`;
  - the same bad pay dates on an instrument outside the run's set, or with an ex-date after `end`, are ignored;
  - a synthetic run without pay dates still uses `DISTRIBUTION_LAG`, with results unchanged.
- [ ] Existing tests pass, with only the authorised helper migrations. CI green; `docs/handoff.md` updated.

### Exclusions
The IBKR export tool (T-011), the exceptions-file parser (T-009 owns it), Gate 3 statistics and enabling real runs, the activation evidence of backtest spec §12, freezing H-001, real or holdout data, FX.
