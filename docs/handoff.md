# Handoff — read this first

## Latest: Codex T-010 requirements review — changes requested

T-010 requirements review at d739684390e00fedcdeedf9bb9687287f9f91ddf: changes requested; no build started.

Independent checks: BT13 matches every ledger field. Saturday payment credits Monday 15 Jan; same-ex-date payment credits Tuesday 16 Jan; the 2 Feb payment remains unsettled at the 26 Jan end. Earlier simulator, schedule, rebalancer, metric and invalid-input fixture sections are JSON-identical to de8f8dc. Independent calculator /tmp/review_t010.py also reproduced all 11 earlier simulator cases, schedules, RB1–RB4 and MT1. No market data used.

B1 — Schema provenance is missing from the proposed bridge's input.
market_from_raw(raw_dataset, exceptions_snapshot) must reject v1 and accept v2, but accepted RawDataset has only prices/distributions/calendar/declarations/partition/holdout_start; read_raw_dataset returns the manifest separately. Neither RawDataset nor ParsedImport carries a schema version. A v2 dataset with all opens None and no distributions has exactly the same record content as a v1 dataset, so inspecting fields cannot distinguish them. Likewise trader-split cannot infer the original CSV version from an empty-distributions/all-missing-opens import.
Specify explicit schema propagation from header -> parsed import -> partitions -> read result -> bridge, or change the bridge to consume a validated dataset-plus-manifest envelope. Do not infer version from non-None records or let an unverified caller label substitute for manifest validation. Include empty-distribution and all-None-open tests proving v2 remains v2 and an equivalent v1 is refused; preserve v1 byte identities.

B2 — A date-only payment field does not prove cash is available at that session's open.
The rule credits cash at the start of the pay-date session before fills. For an ordinary weekday pay date, an account credited later that same day would nevertheless fund a morning buy in this simulator. A payment date alone cannot distinguish those two cases. The spec also assumes every final historical pay date was announced before ex-date, but neither the declarations nor event schema establishes this.
Keep BT13 as a test of the declared model if desired, but explicitly label same-pay-date opening availability as an assumption, not a guarantee that cash is never used early. Before real activation, require evidence of broker spendable-cash timing or an owner-approved lag/next-session convention with a sensitivity check. Specify evidence that exported pay dates reflect the schedule known at ex-date, or explicitly gate use of retrospectively revised dates. Pay_date can remain an event attribute exempt from holdout partitioning; the exemption needs a stated point-in-time evidence condition. No network/broker work is requested in T-010.

Contract cleanups to settle with the revision:
N1 — Requiring schema with no default breaks every existing write_raw_dataset call (including tests); adding pay_date also changes asdict-based CSV test exporters. “Existing tests unchanged and pass” cannot coexist with this API change. Choose compatibility or explicitly authorize mechanical caller/helper migrations while keeping all prior assertions and fixture answers. Also name the error for unknown schema arguments.
N2 — Backtest §2.1 still says raw storage refuses every non-None open until a later card, contradicting the new v2 support. Registry §5.4 still says the open-prices card enables SUPPORTED_REAL_SCHEMAS whereas T-010 now defers activation to statistics; align it without enabling real runs. Decision 0011 row 3 references decision 0010 row 18, which does not establish the lag rule (the relevant discussion was decision 0009).
N3 — Define BACKTEST_PAY_DATE for wrong-type non-None values, not only pay_date < ex_date, to avoid unlabelled TypeError for direct canonical inputs. Specify v2 writer validation of both missing and pre-ex-date payments and tests for invalid pay dates outside the run instrument/end scope being ignored consistently with admission.
N4 — “T-009 and T-010 share no code” is inaccurate if T-010 moves the exceptions parser into trader.data for registry reuse. Assign that shared parser location/ownership before parallel builds, or make that small integration sequential. The accepted digest and approved-string contract must remain unchanged.

PR #15 is still awaiting the owner's merge; this review does not authorize either merge or build. Current strategy remains unchanged; real execution remains blocked.


## Latest: T-010 card drafted (Claude) — 2026-10-16

Branch `t-010-card`, built on `t-009-card` (PR #15, accepted, awaiting the owner's merge). Docs and fixture only.

Contents:
- **Data spec v1.3:** optional `open` and `pay_date`; raw-dataset schema v2 and CSV v2 (§8.4.1); §10 row updated.
- **Backtest spec v1.3:** pay-date settlement (first session after the ex-date on or after the pay date); `market_from_raw` (v2 only); `BACKTEST_PAY_DATE`.
- **Fixture v1.3:** adds BT13 (Saturday, same-day and beyond-calendar pay dates) from Claude's calculator; all earlier cases unchanged.
- **Decision 0011:** the design choices. Real runs stay refused until the Gate 3 statistics card. Distribution history comes from issuer sources; the IBKR export is T-011.
- **`docs/tasks/T-010-opens-pay-dates.md`.**

The growth pivot (draft PR #16) is undecided; the current strategy is unchanged.


## Codex accepts T-009 v3.1 requirements

Accepted at `018157b82fd73635c07bcbd469fc27d9c410634b` (PR #15), registry spec v1.2.1. B1–B7 resolved; no remaining blocking findings. This is requirements acceptance, not implementation acceptance.

Completed checks: independently decoded the non-empty §5 example, keeping `approved` as its round-tripping ISO string. With the existing shared helper the digest is `369a53d5a021701d2e156efe684ea657e9e0a0bcc0d02d143e5c4990a5d793db`. A synthetic 100→150 jump on 2024-01-08 passed to the accepted builder in research mode produced only `DATA_JUMP_APPROVED`, with `data_ok=True` and the same digest. Command: `PYTHONPATH=src /tmp/trading-t007-build/.venv/bin/python` with an independent inline reproduction, outside implementation/tests.

Diff against `614084b` confirms source, reference fixtures and H-001 unchanged. Prior vector/validation reproductions remain applicable. GitHub push run 38968000571 and PR run 38968007258 both passed at the reviewed SHA. No full local suite rerun for this docs-only correction.

Next: incorporate this handoff-only acceptance into PR #15; owner merges, then Codex implements the accepted card from main. No build started. Continue the current strategy: no growth pivot, no freezing/registering H-001, no real execution, broker access or funding.


## T-009 v3.1: Codex's B7 resolved (Claude) — 2026-10-16

Registry spec v1.2.1: exceptions-file `approved` is validated as round-tripping ISO but kept as a string (canonical `JumpException`). Card v3.1 adds the non-empty round-trip test (digest `369a53d5…93db`; `build_dataset` gives `DATA_JUMP_APPROVED`). Decision 0010, third re-review section. PR #15; the commit is named in the PR comment.


## Codex T-009 v3 re-review — one correction remains

T-009 v3 re-review at 614084bfa9066530275ffadfd914f46d1fc2b7e7: B5 and B6 resolved. One narrow contract correction remains before acceptance; no build started.

Resolved:
- B5: immutable descriptor -> accepted factory -> simulator provides explicit configuration identity, including schedule; unsupported scripted/custom generators are refused.
- B6: field-level registry validation replaces reliance on Params construction; all declared multipliers are checked.
- Two committed append transactions, committed-HEAD checkpoint provider, resolver-drift test, successful finish event and added lifecycle checks resolve the requested clarifications.

B7 — Exceptions-file decoding changes the approved field to an incompatible type.
Registry spec §5 says both date and approved are decoded using date.fromisoformat, then passed to the shared exceptions_digest. The accepted canonical JumpException has date: date but approved: str (src/trader/data/records.py). The shared helper serializes approved directly, and the builder's _approval_valid also expects a string.

Independent minimal reproduction:
exceptions_digest([JumpException('SYN_A', date(2024,1,8), 'test', date(2026,10,16))])
raises TypeError: Object of type date is not JSON serializable.
Keeping approved='2026-10-16' produces:
369a53d5a021701d2e156efe684ea657e9e0a0bcc0d02d143e5c4990a5d793db

Correction: decode the event date to date; validate approved with date.fromisoformat and round-trip equality but retain its ISO string in JumpException. Add a non-empty exceptions-file round-trip test that computes the shared digest and feeds the parsed entries to build_dataset without DATA_INVALID_EXCEPTION. Do not change the accepted canonical record or digest formula.

Checks completed:
- All 5 chain rows, 8 tamper outcomes and 3 config hashes reproduced again with /tmp/review_t009_v2.py.
- Fixture and H-001 files are unchanged from v2.
- Independent /tmp/check_t009_v3_values.py checked resolved V1/V2/V3 against §1.1 and exact parameter-field coverage. All pass. Known backtest settings pass with synthetic substitutions for draft unknowns; this does not supply evidence or freeze H-001.
- Direct date-versus-string probe above confirms B7.

No further design change requested. Keep real execution blocked and H-001 draft.


## T-009 v3: Codex's B5–B6 and clarifications resolved (Claude) — 2026-10-16

Registry spec v1.2, card v3, decision 0010 rows 15–18 and second re-review section. Fixture unchanged. PR #15; the commit is named in the PR comment.

- **B5:** `RunDescriptor` plus `build_generator` through the accepted factories; the recorded config is the executed descriptor; the synthetic `variant_id` is its config hash; scripted or custom generators refused.
- **B6:** the registry's own value validation (§1.1) for resolved variants and every declared cost multiplier; `REGISTRY_PREREG_INVALID`; draft nulls skip only their own checks.
- **Clarifications:**
  - two transactions per run, with `run_started` committed before the simulator (child-process test);
  - checkpoint read from committed `HEAD` only;
  - strict exceptions-file schema;
  - drifted-resolver test for `REGISTRY_CONFIG_MISMATCH`;
  - explicit `completed` branch;
  - lifecycle checks for `run_id = seq` and `trial_count_after`.


## Codex T-009 v2 re-review — changes requested

T-009 v2 requirements re-review at 74bec2033ee2ffdb23733b65766fadb9ce582a32: original B1–B4 resolved. Two remaining implementation-contract blockers; no build started.

Completed independent reproduction: all 5 chain bodies/hashes, verification with both checkpoints and without a checkpoint, all 8 tamper outcomes/seq values, and all 3 full config hashes matched. Fixture registration count is 2; run 3 is completed, run 5 unfinished, and run 3 superseded. Temporary independent checker: PYTHONPATH=src /tmp/trading-t007-build/.venv/bin/python /tmp/review_t009_v2.py.

Resolved:
B1: durable registration events and event-derived count preserve historical reservations.
B2: registry identity and committed checkpoints cover truncation/replacement, with the uncheckpointed suffix limit correctly documented.
B3: real-run arguments no longer override period/config; registered config, costs, data and cleaning snapshot are bound; baselines have identity.
B4: empty SUPPORTED_REAL_SCHEMAS explicitly prevents real execution and raw-to-Market conversion.

B5 — Synthetic configuration cannot be derived from the current Generator (§5.3 versus §2).
run_synthetic receives market, generator and backtest_params and must derive a full config from them. The accepted Generator exposes only name, instruments, function, schedule, exceptions and exceptions_version. It does not expose Params, asset_class, baseline argument names, or scripted orders; those live inside opaque closures. The strategy generator's schedule is None, so this API also has no weekly/monthly selection input. Two strategy generators with different TOP_N values expose the same ordinary metadata but require different config hashes. The §2 schema has no configuration identity for scripted/custom generators either.
Define a supported explicit immutable run descriptor (or extend factory metadata) containing the exact configuration used to construct the generator, plus schedule; specify supported synthetic generator types and how scripted/custom test runs are identified or refused. Do not infer closure cells or hash guessed defaults. Add tests that different Params/classes/schedules produce the correct differing identities and that the recorded descriptor is the one actually executed. This is a bounded API decision, not a request for a second simulator.

B6 — “Construct a valid Params” is not validation (§1).
Params is a frozen dataclass with no __post_init__ validation. Independently confirmed Params(TOP_N=0), TOP_N=-1, TOP_N=True and TOP_N='bad' all construct successfully. Null-free files can therefore pass the prescribed constructor test while being nonsensical or crashing later. Specify the registry validator's field types/ranges and required relationships for Params/overrides (without changing frozen strategy defaults). Also validate BacktestParams for every declared cost multiplier and relevant instrument: its constructor alone does not call validate_instruments, and a spread admitted at multiplier 1 may produce a nonpositive sell price at multiplier 2. Include invalid-value and overridden-value tests, with the named preregistration error. Draft null placeholders should skip only the checks that require those particular unknown values.

Clarifications to include with those fixes:
- §5's “all writing operations ... one transaction” must explicitly mean separate transactions for start and finish: COMMIT run_started before calling the simulator, then finish in a second BEGIN IMMEDIATE. Holding a single transaction across the simulation rolls back the start on process death. Prove persistence with a child process terminating after start and a separate connection reading the unfinished run.
- The card's config-mismatch example is unreachable as written: editing/recommitting the same file changes file_sha256 and step 3 raises HYPOTHESIS_CHANGED before step 4. Use a resolver-drift/registered-hash mismatch test for CONFIG_MISMATCH, preserving the stated error order.
- Define exceptions_file's serialization (exact version/entries schema and date decoding), and how API checkpoint arguments are verified as the committed checkpoint rather than accepting an arbitrary caller-provided older one. Tests can inject the committed-checkpoint provider.
- Explicitly specify run_finished outcome='completed' with metrics/totals on success in §5.5, in addition to the failure branches. Verify run_started.run_id equals its seq and registration trial_count_after equals the derived count.

The redesign fixes the original audit gaps; the remaining blockers concern implementing its promised provenance and validation faithfully. No changes to strategy settings or fixture values are requested.


## T-009 v2: Codex's B1–B4 and N1–N3 resolved (Claude) — 2026-10-16

All accepted; details in decision 0010 (rows 4–6 amended, rows 10–14 added, re-review section). Registry spec v1.1, fixture v1.1, card v2 on `t-009-card` (PR #15); the commit is named in the PR comment.

- **B1:** `hypothesis_registered` events; `trial_count` read from the registry only, so deleting, demoting or renaming a file never lowers it; ids are immutable.
- **B2:** `registry_created` genesis with a `registry_id`, plus a committed checkpoint (`registry_id`, `seq`, `row_hash`) to detect truncation and replacement. Limits are stated: rows after the last checkpoint, and internal-only verification.
- **B3:** runs are bound to the registered config hash, exact period (no caller window), declared cost multipliers, pinned dataset and exceptions snapshot. Baselines have ids and configuration hashes.
- **B4:** `SUPPORTED_REAL_SCHEMAS` is empty, so real execution always gives `REGISTRY_REAL_DATA_UNSUPPORTED` with no row; synthetic runs take an explicit market, generator and params.
- **N1–N3:** strict parsing rules; lifecycle and `BEGIN IMMEDIATE` concurrency; ordinary exception, process death and logging-failure semantics; fixture rebuilt with full valid events, independently verified tamper cases, and full configuration vectors. Stale backtest header fixed.


## Codex T-009 requirements review — changes requested

T-009 requirements review at 60623a43c5ea9f365a0a8a369ac0ab137f977aad: changes requested. No build started.

Independent checks: all three chain hashes, all three tamper first_bad_seq answers and config_hash reproduce exactly. H-001's Params and BacktestParams field sets match the code. The backtest §6.2 amendments match the accepted implementation. Keeping V1 primary and V2/V3 non-promotable is clear.

B1 — Trial history can shrink (registry spec §§5–6; charter §6 permanent rule 1).
trial_count is calculated only from currently present frozen files. Freeze/use H-001 with V1–V3, then delete that file (or change its status to draft) in a clean committed checkout: the prescribed count falls from 3 to 0 even though its runs remain. File pinning only checks a subsequent run of that hypothesis; it does not preserve the budget when a different H file runs. Reserved-but-never-run variants are also lost. Define durable registration/accounting of frozen hypotheses and all declared variants, with immutable identities and inherited history. Missing/changed historical files must not reduce the count. Add deletion, draft-demotion and new-charter tests; specify whether these operations fail or retain the historical reservation.

B2 — The hash chain cannot detect suffix deletion (spec purpose, §3; decision 0010 row 6).
Using the fixture, remove final seq 3: the remaining chain verifies without changing any hash, hiding its unfinished run. An empty replacement log also passes the stated sequence/hash check. This does not require recomputing later hashes, contrary to §3. Either introduce an independently retained expected head/length with a defined checkpoint/recovery procedure and tests, or explicitly limit verification to internal chain consistency and require a pinned external checkpoint to detect truncation/rollback. Remove the “impossible to lose/edit/hide any run” promise. Backups alone are not a verification algorithm. Include a final-row/suffix-deletion reference case with the chosen expected behavior.

B3 — The frozen contract does not fully constrain the actual run (spec §§1–2, §5).
The API accepts period and cost_multiplier, but the gate only requires the period to be inside the dataset. A frozen 2015–2021 period can therefore become 2020–2021 under the same variant. Arbitrary positive cost multipliers likewise have no explicit refusal rule. The exception snapshot is recorded but not pinned in the hypothesis: changing approvals can change decisions while hypothesis hash, dataset hashes and config_hash remain identical.
Require the actual period to equal the frozen period (or a separately declared window), costs to be only the predeclared base/stress choices, and the cleaning snapshot version/digest to be frozen and verified. Specify a baseline identifier and its effective configuration in the event/hash: kind=baseline alone does not identify sixty_forty versus moving_average_10m etc. Add refusal cases for each undeclared change and exact event/config examples. Recording a changed value is not enforcing pre-registration.

B4 — The real-data prerequisite is not enforced (spec §5 versus backtest §12 and task exclusions).
A complete temporary frozen file plus an existing v1 development raw dataset meets every listed real-mode check today. But v1 storage has no opens; converting it to Market yields open=None throughout, allowing a meaningless no-fill run to be recorded as completed. The required open-price/payment-timing card is explicitly not implemented here. Keep real execution explicitly refused until those prerequisites have a defined supported schema/capability; synthetic tests can exercise the gate checks without authorizing the real path. Define the RawDataset-to-Market boundary (including approvals) and the synthetic configuration input: the displayed run_registered signature supplies neither a synthetic full configuration nor a generator, so “run with the resolved configuration” is currently underspecified. Add a regression proving v1 raw data cannot reach a real simulator execution.

Additional contract clarifications:
N1: state strict validation rules for duplicate JSON keys/variant IDs, non-finite values, unknown override fields, roles/schedules and frozen_by; absence of null is not sufficient validity.
N2: define event lifecycle validation (one finish per started run, valid supersedes references, body seq equals table seq), concurrency/locking for pin/budget checks plus start append, ordinary exceptions versus process death, and recording an error when failure logging itself is unavailable. The blanket “anything after start is recorded failed” is incompatible with the intentionally tested crash case.
N3: chain fixture run_started bodies omit required config; label these as hash-only vectors or make them full valid events. The config vector is partial, so add a full resolved-config vector if it is also intended to exercise schema validation. Update the stale backtest header saying T-008 awaits review.

Reproduction: PYTHONPATH=src /tmp/trading-t007-build/.venv/bin/python /tmp/review_t009.py (independent temporary script outside the repo). All supplied vectors passed; suffix deletion and whole-log replacement returned no chain error, and directory-based count fell 3 -> 0. These are synthetic contract probes, not strategy evaluations.


## T-009 card drafted (Claude) — 2026-10-16

PR #14 (T-008) was merged by the owner's instruction as `7d0e020`. Branch `t-009-card`; the PR and commit for Codex's requirements check are named in the PR. **Docs and fixture only; no code.**

Contents:
- `docs/registry-spec.md` v1.0: pre-registration file contract (one `json preregistration` block; frozen = complete), canonical `config_hash`, SQLite append-only events with triggers and a SHA-256 hash chain, `run_started`/`run_finished` events, the real-data gate (clean checkout, frozen file, pinned development dataset, holdout refused, file pinned at first run, ≤ 20 declared variants), summary with `trial_count`.
- `research/hypotheses/H-001.md` (**draft**): mechanism, rules by reference, variants V1 (primary) and V2, V3 (robustness, never promotable), expected behaviour, Gate 3 falsification. The contract is checked against the `Params` and `BacktestParams` defaults. Half-spreads, distribution lag, dataset and period are `null` until the owner freezes it from evidence.
- `tests/fixtures/registry_cases.json`: hash-chain, tamper and config-hash vectors from Claude's reference outside the repo, verified a second way.
- `docs/decisions/0010-registry-and-preregistration.md`, and backtest spec v1.2.1 (§6.2 traded-set wording and `BLOCKED_NAV`; §12 H-001 variants).
- `docs/tasks/T-009-experiment-registry.md`.


## Claude accepts T-008 implementation — 2026-10-16

**Accepted at `fcfd7da4b31a43d3cd2e7b9381435e66e8eaa567`; no blocking findings** (reviews on PR #14).
- First review at `1242060` found **B1**: a `Market`-supplied exceptions snapshot was silently replaced by the strategy generator's default, so provenance was misrecorded and approved jumps were blocked. Fixed: `Market` is the sole source; a conflicting generator snapshot or version gives `BACKTEST_PARAMS`.
- Non-blocking N1–N3 fixed: rebalancer traded-set convention documented and tested; `BLOCKED_NAV` for baselines; shared `exceptions_digest`.
- Claude's independent harness (outside the repo): every fixture case reproduces with 0 mismatching sessions; BV1–BV8 raise their codes; admission scoping is correct; a 420-session look-ahead probe passed.
- Follow-up for Claude: align backtest spec §6.2 wording (absent from targets = not traded) at the next spec touch.

The owner merges PR #14 pinned to the commit that adds this note.


## PR #14 review fixes — Codex

Claude's B1 at `1242060` is resolved: Market is the authoritative approval snapshot. Generator defaults are None; optional generator values must match the market digest/version or raise BACKTEST_PARAMS. No snapshot is silently replaced. Regression coverage includes an approved synthetic jump supplied only through Market, its recorded version/digest, matching duplicate inputs, conflicting contents/versions and the unapproved control.

N1–N3 addressed: rebalance documents/tests target keys as the traded set; baselines report BLOCKED_NAV for nonpositive NAV; builder and simulator share the exact data-spec exceptions digest helper. The helper extraction preserves the canonical digest formula.

Completed focused checks: 139 tests passed (backtest contract, all numeric fixtures and data-builder fixtures); Ruff passed. Full clean-checkout suite and CI follow this commit; results and exact review SHA are recorded on PR #14. Fixtures and strategy parameters unchanged. Synthetic only. Await Claude re-review; no merge.

## T-008 implementation — Codex, 2026-10-16

PR #13 is merged at `1d4529f`, preserving acceptance `7abbac3`. Implementation is on `t-008-backtest` from that main commit. Backtest spec v1.2 and the fixtures are unchanged; the data-spec §10 amendment was already present on main.

Implemented the optional canonical open (raw v1 storage refuses it), bounded decision/admission adapter, schedules, synthetic simulator, shared-engine strategy generator, baselines, descriptive metrics and T-007 N1–N6. The buy affordability search is logarithmic rather than decrementing one share at a time; non-negative costs make it mathematically equivalent to the specified largest-affordable-quantity loop. Generators declare an explicit instrument set, including scripted generators, so unknown orders cannot expand admission scope. Baselines default to monthly; an explicit different named schedule is refused.

Completed verification at implementation commit `902e3e1`:
- `PYTHONPATH=src /tmp/trading-t007-build/.venv/bin/python -m pytest -q`: **806 passed in 2.72s**, including all fixture cases, synthetic strategy/baseline integration, admission codes, causality, cash/NAV identities, anomaly reporting and all N1–N6 follow-ups. The real chmod test ran (non-root), with no skips.
- `/tmp/trading-t007-build/.venv/bin/ruff check .`: **All checks passed**.
- `git diff origin/main -- tests/fixtures src/trader/signals src/trader/portfolio src/trader/planner src/trader/params.py`: **empty**.
- Clean working tree after the implementation commit; original CLI smoke test passed with the new tracked-dirty guard active.

The CSV test exporter explicitly excludes the canonical `open=None` field (and asserts it is None); CSV acceptance assertions and all fixture values are unchanged. The final handoff-only commit is the PR review head; GitHub CI status and exact SHA are recorded in the PR body.

Synthetic tests only, no evaluation runs or registry entries. No real data, holdout, broker access, funding or spending. Next: GitHub CI, then Claude reviews the exact PR head. No merge authorised.

## Codex accepts T-008 v3 requirements — 2026-10-16

Accepted at `4b896e2b80545224524fc14d18e8843dadbbee0d` (PR #13), backtest spec v1.2. No remaining blocking findings. This accepts the requirements, not an implementation or evidence of trading performance.

- B6 resolved: cost-stress acceptance checks the exact side-dependent fill and commission formulas, without the incorrect monotonic claims. BT11 independently reproduces sell fill 99.70 and commission 9.8703 (base fill 99.85).
- B7 resolved: buy affordability is clamped to zero; BT12 independently reproduces quantity 0, commission 0 and SKIPPED_CASH for both the same-session and next-session buys after SHORTFALL, with no cash or holdings change from either buy.
- Completed: `python3 /tmp/review_t008_v3.py` (independent temporary calculator outside the repo): all 11 simulator cases matched every expected ledger field; weekly/monthly schedules, MT1 metrics and all four rebalancer cases matched.
- Completed: parsed-JSON comparison against `96e9617c11f78bc10cfaf2363ffdce55eec1f44b`: all 9 earlier simulator cases, schedule case, 4 rebalancer cases, 5 metric cases and 8 invalid-input cases unchanged. Only BT11 and BT12 added.
- Completed: GitHub CI verified successful at the reviewed SHA for both push run 38961971954 and PR run 38961978369. No local full-suite rerun for this documents/fixture review.

Next: include this handoff-only acceptance commit in PR #13; owner merges. Then implement T-008 against the accepted card using synthetic data only. No build started in this review; real-data evaluation, broker access, funding and spending remain outside scope.

## T-008 v3: Codex's B6–B7 resolved (Claude) — 2026-10-16

- **B6:** the cost-stress acceptance now checks exact formulas at m = 1 and m = 2 (buys worsen upward, sells downward) with no monotonic claims; BT11 adds a sell-side stress case (99.70 vs 99.85; commission 9.8703).
- **B7:** spec §4 buy affordability is clamped at `max(0, …)`; with settled cash ≤ 0 a buy is `SKIPPED_CASH` with quantity 0; BT12 covers the same-session and next-session cases after a `SHORTFALL`.

Fixture v1.2: earlier cases are unchanged, and the values come from Claude's calculator outside the repo. Spec v1.2, card v3, decision 0009 second re-review section. Branch `t-008-card` (PR #13); the commit is named in the PR comment.


## Codex T-008 v2 re-review — 2026-10-16

**T-008 v2 re-review at 96e9617c11f78bc10cfaf2363ffdce55eec1f44b: B1–B5 resolved. Two small contract corrections remain before acceptance; no build started.**

## Resolved
- B1: absent observations are distinct from invalid supplied closes; rebuilt BT5 admits a genuine gap and BV1 requires invalid-close refusal.
- B2: explicit run-instrument/date scoping, decision-time exception filtering, separate full-snapshot provenance and admitted-input leakage tests are consistent.
- B3: short series, zero/negative NAV and zero stdev have defined None/reason outcomes while retaining the ledger.
- B4: lags >=1, pending lots beyond end, and the explicitly conditional real-data payment-timing prerequisite resolve the ambiguity and unsupported guarantee.
- B5: finite cost validation, positive fill-price constraint, generator-order validation and explicit decision-date validation cover the reported invalid inputs.
The MA missing-history behavior, baseline convention and data-stale wording are also clarified.

## B6 — Cost-stress acceptance still asserts the wrong sell-price direction

T-008 card, Cost stress: “For any single fill, the doubled fill price and commission are at least the base ones.”

For a fixed sell of 100 shares, open=100, half-spread=.001 and slippage=.0005:
- m=1: fill=99.85;
- m=2: fill=99.70.

The spec's sell formula is correct, but the acceptance criterion contradicts it. Nor is commission universally monotonic across the entire admitted parameter domain, because it is charged on the changed fill notional: with quantity=1000, open=100, half-spread=.4, slippage=0, rate=.0005 and minimum=3, m=1 gives sell fill=60 and commission=30; m=2 gives fill=20 and commission=20. Both satisfy m*c<1.

Replace the monotonic fill/commission assertion with direct formula checks for fixed open, side and quantity: buys worsen upward, sells worsen downward, spread/slippage cost scales with m, and commission equals max(m*minimum, m*rate*q*fill). Keep aggregate costs unconstrained when quantities differ. Add a sell-side stress case; BT7 only exercises a buy. No change to the cost model is requested.

## B7 — Affordability must clamp to zero after a permitted shortfall

Spec §4 initialises buy quantity as min(ordered, floor(settled/f)), then only reduces it while q>0. The spec also deliberately permits negative settled cash after a SHORTFALL sale.

Using BT6's settled=-1.991, a later scripted BUY 1 with fill price about 1 gives q=-2. The loop is skipped, yet no status/cash rule handles q<0. Scripted orders are valid positive-integer orders; strategy-level blocking does not protect the simulator's general fill boundary. A same-session earlier shortfall sale followed by a buy is another route.

Clamp affordability to max(0, ...) or explicitly return SKIPPED_CASH with quantity 0, commission 0 and no holdings/cash change whenever settled cash cannot fund a share. Test a valid BUY after a SHORTFALL, including sells-before-buys in the same fill session. The ledger may retain its permitted negative balance, but a buy must never have a negative quantity.

## Independent checks

Temporary calculator outside the repo: `python3 /tmp/review_t008_v2.py`, plus a standard-library metric/edge-case check.
- All **19 numeric reference cases** matched their recorded values: BT1–BT7, BT9–BT10 (all ledger fields), BT8 schedules, RB1–RB4 orders and MT1–MT5 recorded metrics/undefined reasons.
- BT9's final settled cash is 4,975.50 with 100 SYN_B; BT10 ends with 1,006.50 unsettled and NAV 10,003.
- MT2 short-series annual return 11.274002099240244, vol/Sharpe None; MT3/MT4 insolvency date 2024-01-10; MT5 zero vol and ZERO_STDEV Sharpe.
- BV1–BV8 are descriptive rejection cases rather than fully populated executable fixtures. Their expected codes match the amended contract; implementation tests will instantiate the described inputs.
- Independently calculated the B6 sells above and B7 floor(-1.991/1)=-2.

No implementation, strategy evaluation, real/holdout data, broker access or merge. Only this review handoff is edited. Claude should make the two narrow corrections and add the regression expectations, then return for acceptance.


## T-008 v2: Codex's findings B1–B5 resolved (Claude) — 2026-10-16

All accepted; details in `docs/decisions/0009-backtest-simulator-design.md` (re-review section, rows 14–19). Backtest spec v1.1 and card v2 on `t-008-card` (PR #13); the commit for re-check is named in the PR comment.

- **B1:** an absent observation is the absence of a record; `close = None` is invalid and refused at admission. BT5 was rebuilt, BV1 added, and last-close valuation is always defined.
- **B2:** admission is scoped to the run's instrument set and to records ≤ `end`. New spec §2.3 point-in-time adapter: calendar, records and exception entries dated ≤ d, a whole-snapshot fingerprint, and the published calendar only for schedule and lags. The leakage property applies between admitted inputs.
- **B3:** undefined metrics are `None` with a reason (`NON_POSITIVE_NAV` + `insolvent_on`, `SHORT_SERIES`, `ZERO_STDEV`); fixtures MT2–MT5.
- **B4:** lags are integers ≥ 1 with settle-before-fill timing; BT9 (lag 1) and BT10 (pending at `end`). The 20-session distribution lag is a declared assumption, with a real-data pay-date prerequisite.
- **B5:** `BACKTEST_COSTS` (every fill price positive), `BACKTEST_ORDER`, `BACKTEST_SCHEDULE`; fixtures BV1–BV8.
- **Notes:** cost-stress acceptance reworded; exits-never-blocked labelled a simulation assumption; `DATA_STALE` wording fixed; moving-average "not traded" pinned; global-equity convention in protocol §5.
- **Fixture v1.1:** all new values come from Claude's calculator outside the repo. The earlier cases are unchanged apart from BT5 (rebuilt) and MT1's added `insolvent_on`/`undefined` keys.


## Codex T-008 requirements review — 2026-10-16

**T-008 requirements: Changes requested. No implementation started.**

Reviewed the requested `ebf34a00ab9b095d42f07858433e5f7d1331883e`. During review PR #12 merged and PR #13 advanced to `9961f02cca52548ce84681d0c896aac94b3fe0f1`; the backtest spec, T-008 card and fixture are unchanged between those revisions. The findings apply to both. The T-007 merge dependency is now satisfied.

## Independent reference reproduction

A temporary standard-library calculator outside the repo (`python3 /tmp/review_t008.py`) reproduced **all 13 cases**: BT1–BT7 every expected ledger field, BT8 weekly/monthly dates, RB1–RB4 orders, and every MT1 metric, within the specified tolerances. Buy affordability was independently calculated using the closed-form minimum of the fixed-fee and proportional-fee cash bounds. This checks the reference arithmetic; it does not resolve the contract contradictions below.

## B1 — BT5 is refused by the mandatory preflight

Spec §2.2 requires BACKTEST_DATA_EXCLUDED for an excluding builder error over the run, but BT5 includes SYN_A on 2024-01-10 with close=None and open=101. The accepted builder reports DATA_INVALID_PRICE and excludes that instrument. I reproduced that exact report using BT5 inputs. Thus a compliant run cannot also return BT5's expected stale-valued ledger.

Define the intended missing-close representation and boundary explicitly. If the simulator retains an open while treating an absent close as a gap, specify its projection into the unchanged builder and distinguish an absent observation from an invalid supplied price; alternatively amend the data contract with explicit tests. Do not silently drop erroneous prices or exempt scripted cases from the promised preflight. Add tests for both a genuine missing observation and an invalid supplied close. Also define valuation if an instrument bought at an available open has never had a known close; “last known close” is otherwise undefined.

## B2 — Point-in-time adapter and leakage property need a consistent contract

Spec §6.1 says to call build_dataset with calendar up to d but does not define the records/exception subset. Passing full records produces DATA_FUTURE_RECORD at every early decision. Filtering prices alone still leaves future-dated entries in the frozen exceptions snapshot outside that prefix calendar, producing DATA_INVALID_EXCEPTION and BLOCKED_DATA. Both effects reproduce with the existing builder on three synthetic sessions.

Specify:
- preflight records bounded through end and the exact relevant instrument set;
- decision records bounded through d, including distributions;
- how the frozen exception snapshot is validated, scoped and fingerprinted without a future entry falsely invalidating an earlier decision;
- whether the known full exchange calendar is retained for validation/schedule lookup while market observations are bounded;
- benchmark versus strategy instrument scoping (the eleven-data-instrument bundle includes benchmark-only VWRL).

Additionally, §9's unconditional “changing any data after d leaves every decision at d unchanged” conflicts with full-run rejection: adding a duplicate at a later session changes an admitted run into BACKTEST_DATA_EXCLUDED before any decision exists. Keeping fail-closed admission is reasonable, but explicitly distinguish admission validation from causal decisions: state the leakage comparison's domain (e.g. both datasets pass admission), and test invalid future-data rejection separately. The adapter must not use future values to select historical trades.

## B3 — Metrics have no outcome for permitted short or bankrupt runs

start < end permits a two-session run: T=1 gives one daily return, so sample stdev(ddof=1) is undefined. Only the zero-stdev case currently has a rule.

BT6 deliberately produces NAV=-1.991 from initial 4.01, and zero NAV is also possible. Return ratios divide by zero after a zero NAV; annualising a negative terminal ratio can be non-real (for example extend the negative-ending ledger to T=5). This is not covered by “still a valid record.” Define the metric contract for short series, zero/negative NAV and non-positive mean NAV: preserve the ledger and report named undefined metrics/reasons, or define a recorded insolvency termination policy. Do not silently clamp or output complex/NaN performance statistics. Add short, zero-crossing and negative-NAV fixtures.

## B4 — Settlement rules need zero-lag and pay-date semantics

Both lags allow zero, but settlement occurs before new distribution/sale lots are created. A lot created at d and due at d is therefore not spendable until the next session under the literal loop. Define same-session availability explicitly (including whether a zero-lag sale can fund a later buy at that open), or disallow zero. Add cases for lag 0, lag 1, and lots still pending beyond end/the supplied calendar.

Decision 0009 also claims an assumed 20-session distribution delay ensures cash is never available earlier than reality. Without a pay date or evidence establishing that bound, that does not follow: a payment on session ex+25 would be credited five sessions early. Keep 20 as a declared synthetic assumption if desired, but remove the guarantee and specify the real-data prerequisite for payment timing (or an explicitly approved approximation and sensitivity policy). Do not call it inherently conservative.

## B5 — Fill inputs admit non-positive execution prices and malformed orders

The current spread condition permits any finite nonnegative value; costs/multiplier have no combined upper bound. HALF_SPREAD=1, SLIPPAGE=.0005 and m=1 gives a negative sell fill at a positive open (open=100 -> -0.05). Costs and the multiplier must be finite, and the computed execution prices must be positive (for example require m*(half_spread+slippage)<1, with a named refusal).

Define the order-generator boundary too: known instrument, BUY/SELL side, positive whole-share quantity, and a policy for duplicate/conflicting orders. A negative or fractional scripted quantity must be rejected, not allowed to violate §9's holdings/cash invariants. Specify validation for decision_dates (unique, increasing, eligible sessions with a next fill inside the run). These are simulator input guarantees, not broker execution approval.

## Non-blocking amendments / implementation clarifications

- The cost-stress acceptance must not promise higher *aggregate* costs for arbitrary runs. Example: cash £10, open £6, order 1, zero spread/slippage/rate, minimum £3: base fills and costs £3; double minimum £6 prevents the fill and costs £0. Check per-unit/per-order cost formulas, BT7, and report changed fills/turnover rather than asserting universal monotonic totals.
- “Exits never blocked” is an explicit simulation assumption, not the engine's data-safety rule and not Phase 4 permission to borrow for fees. Decision 0009 #7 should not claim equivalence to that rule. SHORTFALL records are operationally infeasible under the later nonnegative-cash gate and must stay visible.
- §2.2 incorrectly groups DATA_STALE with data_ok=false flags: the accepted builder leaves data_ok true for stale-only data; held missing history blocks through the planner. Align the wording/status test with the existing engine.
- Pin the handling of an MA instrument lacking ten usable month-ends as “do not trade,” not a zero-target exit, including if it is already held. Use the known schedule so the current month-end is included despite a market-data cutoff at d.
- Global equity is now a monthly band/reinvestment baseline, whereas the protocol calls it buy-and-hold. State that precise convention in the protocol/decision record; do not imply distributions are reinvested immediately.
- The newer branch correctly includes decision 0008 and T-007. Preserve that updated handoff when incorporating this review; no replacement implementation is needed.

No source or fixture was edited. Only synthetic fixture calculations and small probes against the accepted builder were run; no strategy evaluation, real/holdout data, broker access, spending or merge. Existing implementation CI is not evidence that this new simulator contract is consistent. Claude should resolve B1–B5 in the spec/card/decision record and add the boundary reference cases before acceptance.


## T-008 card drafted (Claude) — 2026-10-16

Branch `t-008-card`; the PR and commit for Codex's requirements check are named in the PR. **Docs and fixture only; no code.**

Contents:
- `docs/backtest-spec.md` v1.0: session loop; fills at the next open with spread, slippage and min/rate commission; buy affordability at the fill; T+2 settlement; distribution entitlement and lag; stale valuation; ISO-week and month schedules; strategy generator over the unchanged engine; band rebalancer for baselines (60/40, global equity, 10-month MA, cash); run metrics; required properties.
- `tests/fixtures/backtest_cases.json`: 7 scripted simulator cases, schedules, 4 rebalancer cases and 1 metrics case, from Claude's independent calculator outside the repo. The metrics case is cross-checked by a second computation.
- `docs/decisions/0009-backtest-simulator-design.md`: 13 design choices made before any run, plus a data spec §10 amendment (optional `open` field now; raw-dataset schema v2 in a later data card).
- `docs/tasks/T-008-backtest-simulator.md`, including Claude's T-007 review notes N1–N6 as follow-ups.

PRs #11 (`b9828c1`) and #12 (`0805908`) are merged; main is merged into this branch, so T-008 can be built on it once accepted.


## PR #11 merged; PR #12 brought up to date (Claude) — 2026-10-16

PR #11 (decision 0008) was merged by the owner's instruction as `b9828c1`, pinned to Codex's acceptance handoff `7b17650`. Main was then merged into `t-007-storage` for PR #12. This changes docs only: the T-007 code accepted at `eceba59` is unchanged. Both handoff records are kept below, decision 0008 first, then T-007.

**Next:** the owner merges PR #12 (T-007), then Codex checks the T-008 card (PR #13).

## Codex decision 0008 acceptance — 2026-10-16

**Decision 0008 / PR #11 accepted for consistency at 0567670d302c2af97252c8a4fb79eb308e855963.** No blocking findings remain. Owner decisions are unchanged.

B1 is resolved: charter and decision record explicitly list ten strategy instruments, VWRL as benchmark-only, and eleven distinct data instruments; 60/40 reuses VGOV. VDTS is marked dropped rather than silently replaced.

The alignment changes are accepted:
- Three variants reserved, zero run; the primary counts, each comparison changes one factor, and combined changes would require another variant.
- Exact hypothesis files are still required before runs, and candidate selection is frozen before the one-use holdout.
- Four-year rule is consistent with protocol §3; owner proposal → charter confirmation → split → development access preserves the isolation sequence.
- Valid-close counts, including benchmark coverage, are the binding sufficiency test; approximately eight years is only a screen.
- Account observations remain owner-reported or pending; VWRP/IGLT results do not verify the configured VWRL/VGOV lines.
- T-007 is correctly identified as already implemented and accepted by Claude, awaiting owner merge.

Minor non-blocking cleanup: the dropped VDTS row in Table B's supplementary checklist still says “BLOCKED: account pending”; “not applicable—dropped for v1” would be clearer. The sentence claiming any post-October-2018 launch cannot qualify should remain an approximate dated screen, not override actual counts or the eventual end session E.

Evidence: exact-commit documentation diff checked against the prior review, charter, protocol and instrument-role table. Source and tests are unchanged against main 7aad2a9. No suite rerun for this documentation-only review, no external instrument/feed verification, and no data or broker access. This acceptance is not permission to merge, fund or trade.

Owner may merge PR #11, preserving both this acceptance and PR #12's implementation/review handoff when resolving their shared-file conflict. No second T-007 build is needed.


## decision 0008 amended for Codex's consistency review (Claude) — 2026-10-16

All points accepted; the owner's decisions are unchanged. Branch `owner-decisions-2026-10-16` (PR #11); the commit for re-check is named in the PR comment.

- **B1:** the strategy universe is **10 instruments** (VUKE, CSP1, VERX, VJPN, VFEM, VGOV, INXG, SGLN, CMOP, IWDP). **VWRL is benchmark-only**, giving 11 distinct data instruments; the 60/40 benchmark reuses VGOV. VWRL is not added to selection. My earlier "11-instrument universe" was wrong.
- **Trial accounting:** 3 of 20 reserved (primary + two one-change comparisons), 0 run. The comparisons are orthogonal (1/3/12 weekly; 3/6/12 monthly). Hypothesis files are still required under protocol §1. One-use holdout: the candidate is frozen on development evidence before any holdout inspection.
- **Alignment:**
  - "≈ 8 years" is now labelled a screening shorthand; the binding test is the valid-close count, for benchmark inputs too.
  - Protocol §3 points to the 4-year rule.
  - Holdout sequence: proposal → charter confirmation → split → only then development data to agents.
  - Feasibility header and Tables A/C: owner-reported approval, checks PENDING, nothing marked verified. The VWRP/IGLT probe is noted as not covering the configured lines. VDTS is marked dropped.
- **T-007:** implemented in PR #12, **accepted by Claude at `eceba59`** (review on PR #12), awaiting the owner's merge. No new T-007 build.

## Codex decision 0008 consistency review — 2026-10-16

Consistency review of PR #11 at **da352357d80d58de88840ac4ea8bcb7004c298f0**. Owner decisions respected; **one documentation blocker before merge**, plus alignment notes. No strategy or owner decision changed.

## B1 — Clarify the strategy universe versus benchmark-only instruments

Decision 0008, charter §6 and handoff say the strategy universe is now 11 instruments after removing VDTS. Table B actually lists eleven strategy-role candidates before that removal plus VWRL explicitly labelled “Benchmark: global equity.” Removing VDTS leaves ten strategy candidates:
VUKE, CSP1, VERX, VJPN, VFEM, VGOV, INXG, SGLN, CMOP, IWDP.
VWRL is the eleventh distinct data instrument when benchmark coverage is included; the 60/40 benchmark reuses VGOV.

Please list the intended strategy and benchmark-only sets explicitly. If the intention is to preserve Table B's roles, write “10 strategy instruments plus VWRL for benchmarks (11 distinct data instruments)” and mark VDTS dropped in Table B. Do not silently add VWRL to portfolio selection to make the count 11. If eleven tradable strategy instruments are intended instead, that needs an explicit owner choice identifying the extra instrument. This is a scope/configuration ambiguity, not an objection to dropping Treasuries.

## Checks that pass

- SGLN's named conditional exception is explicit; approval still depends on owner account evidence.
- Trial accounting in decision 0008 is correct: **primary + two robustness variants = three reserved variants out of 20**, not two total. No completed backtest trials are evidenced. Say “three reserved, zero run” consistently; the primary is not free. Protocol §1 hypothesis files must still be committed before testing. The document's selection of variants is not a substitute for those exact pre-registrations.
- Pre-registration should make the comparisons orthogonal: 1/3/12 with weekly scheduling, and 3/6/12 with monthly scheduling, all else fixed. Combining both changes would be another variant, not silently included in these two. Every run still gets a registry row; the budget counts variants under §2, not simply all reruns.
- Date arithmetic: 2027-03-08 minus 2026-10-19 = 140 days, exactly 20 weeks. The written one-extension rule is explicit.
- £600/year remains a ceiling rather than spending authority; paper-first and the separate live charter remain intact.
- Four-year holdout selection remains performance-independent and subject to history sufficiency. Exact dates are still unset.

## Alignment notes to fix with the documentation amendment

1. “About eight years” is a useful feasibility shorthand, not an exact inception-date test or a proof of sufficiency. The binding rule is 1,009 valid development closes before H plus the T-007 holdout conditions. Missing/invalid data and the common usable development period can still disqualify an older fund. The actual data depth must be checked for the chosen lines, including benchmark inputs. Proxy use remains research-only and separately reported; it is not an automatic remedy.
2. Protocol §3 still says 3–5 years; point it to the owner's confirmed four-year rule. The handoff's “date set when real data is first split” should say: owner-only proposal -> charter confirmation -> split/copy development. Confirm before data enters an agent-accessible location, not only before performance calculations.
3. Table A and the feasibility header still say account approval pending. Update to owner-reported approved/remaining checks pending, without marking cash-account status, permissions, entitlement or full-history adequacy verified. The reported VWRP/IGLT probes do not verify the configured VWRL/VGOV lines.
4. Keep the one-use holdout rule explicit in the future hypothesis cards: comparisons do not each get a fresh final exam; candidate selection must be frozen using development evidence before any holdout inspection.
5. The handoff now trails implementation: **T-007 is already in PR #12 at eceba59abdffd92500f73fafa2f07ad79d94b170**, 714 local tests and both CI runs passed, awaiting Claude's independent review. Do not start another T-007 build.

Evidence: reviewed the exact five-file documentation diff against charter, portfolio spec, T-007 and research protocol; counted Table B's role-labelled rows; independently calculated the 140-day interval. No tests rerun for this docs-only review. External product inception/availability and IBKR statements were not independently verified; this is an internal-consistency review, not approval of a feed or instrument. No broker access, real data, spending, code changes or merge.


## owner decisions recorded (Claude) — 2026-10-16

PR #10 (T-007 v3 card + data spec v1.2.1) was merged by the owner's instruction as `7aad2a9`, pinned to `a132d34`. **Codex: implement T-007 from main.**

The owner then made seven pending decisions, recorded in `docs/decisions/0008-owner-decisions-2026-10-16.md` on branch `owner-decisions-2026-10-16` (PR named in the PR comment):

1. **D1 gold kept:** SGLN is the one named non-UCITS exception, if the account can trade it.
2. **D2 GBP-hedged Treasuries dropped for v1:** no line passes the ≈ 8-year screen. **10 strategy instruments + VWRL benchmark-only** (11 data instruments), as corrected after Codex's review.
3. **R-002:** 3/6/12 is primary; 1/3/12 is a pre-registered robustness variant.
4. **R-006:** weekly is primary; monthly is a pre-registered robustness variant (3 of 20 reserved including the primary; 0 run).
5. **Stop rule:** calendar weeks from Mon 2026-10-19; checkpoint Mon 2027-03-08.
6. **Budget and paper-first confirmed:** £600/yr is a cap, not an approval.
7. **Holdout rule confirmed:** 4 years by the T-007 proposal rule. Sequence: owner-only proposal → charter confirmation → split → development data to agents.

No performance has been computed on any data. Codex: check 0008 for consistency with the charter, protocol and specs. No code or spec changes.

## Claude accepts T-007 implementation — 2026-10-16

**Accepted at `eceba59abdffd92500f73fafa2f07ad79d94b170`; no blocking findings.** The full review is on PR #12.
- Every card output and acceptance case is met. CI is green on that commit.
- Independent probes (outside the repo): CSV edge cases and preflight path cases behave as specified.
- Non-blocking notes for a follow-up:
  - N1: record or refuse a dirty checkout in `code_commit`;
  - N2: catch `pa.ArrowException` in `read_raw_dataset`;
  - N3: a real unreadable-file test;
  - N4: report all leftovers in one error;
  - N5: README "UTF-8 without BOM";
  - N6: document `SPLIT_PARTITION_MISMATCH`.

The owner merges PR #12 pinned to the commit that adds this note. Next card: T-008 (backtest simulator, cost model, baselines; synthetic first).

## T-007 implementation ready for Claude review — 2026-10-16

Branch `t-007-storage`, isolated checkout from merged main `7aad2a9` (PR #10,
accepted T-007 v3/data spec v1.2.1). The implementation PR names the exact final
review commit and records CI results for that SHA. **State: Review; not accepted
or merged.** Claude performs the independent implementation review next.

Implemented CSV parsing and named boundary errors, public development-only import,
immutable raw records/declarations, deterministic Parquet write/read with full
manifest verification, the owner-only split CLI and proposal mode, holdout-date
proposal, `INVALID_MODE`, and owner instructions/recovery in the README. PyArrow
23.0.1 is pinned in uv.lock; existing dependency versions are unchanged. All data
used in development and tests are synthetic. The program has no network or broker
calls. Engineering dependency installation and GitHub publication used network;
no market data was downloaded.

Completed locally under Python 3.12:
- `UV_CACHE_DIR=/tmp/trading-t007-cache /tmp/trading-build-tools/bin/uv sync --locked`
  installed the locked environment. Initial offline attempt lacked cached tools;
  installation then succeeded.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/python -m pytest -q`: **714 passed**, including all 625 existing tests
  and 89 new T-007 acceptance/regression cases.
- `.venv/bin/trader-split --help`: entry point works.
- `git diff --check`: passed.
- Existing fixtures, strategy parameters and specifications unchanged.

Coverage includes exact CSV errors/file/line, all three market-date boundaries,
after-boundary attestations, deterministic identities and Parquet bytes, independent
hash calculation, provenance digest, corrupt files/metadata/schema, rehashed but
semantically invalid input, exact partitions, empty partitions, source/symlink/
output preflight before reads, case-insensitive prospective aliases, caught rollback,
subprocess `os._exit` interruption and retry/owner cleanup, valid-close counts and
leap convention, and CLI proposal/split execution. No historical performance run.

Routine implementation choices for review:
- Internal full-history parser is `_parse_csv_dir`; the public import is guarded.
  Errors without a physical source row use line 0. Missing declaration reports
  `declarations.csv:0`; empty numeric close remains None for builder validation.
- Source imports reject undeclared/extra/duplicate declarations. A partition
  intentionally retains source declarations even for an instrument with no records
  on that side; this implements the requirement to copy all declarations unchanged.
- Manifest result is a dictionary; `manifest_digest` is returned alongside fields,
  never embedded in the bytes it hashes. Reads decode the same bytes they hashed,
  reject symlinked dataset files and enforce exact Arrow column schemas.
- Rows use stable full-row tie-breakers without deleting duplicates. Storage does
  not turn bad market values into valid prices; the builder still reports them.
- Publication is per dataset, with file/directory sync before proceeding to the next
  rename. Existing outputs are never overwritten. Concurrent splits/path mutation
  are unsupported and documented; containment is not a security sandbox.
- CLI records the implementation checkout's Git HEAD, so the owner must use a clean
  checkout of the reviewed commit. Proposal mode needs no output/provenance flags.

CI is separate from local verification; exact-head results and links are maintained
in the implementation PR. Owner-reported IBKR observations remain unverified by
agents. Real use still requires D5 evidence, declarations and a charter-confirmed
holdout boundary. No funding, broker calls, real data, holdout access, experiments,
purchases, merges or deployment performed.


## Codex T-007 v3 acceptance — 2026-10-16

**T-007 v3 Accepted** at exact commit `abc2f474b3a073eccd20176173e9215e58e92943` (data spec v1.2.1, decision 0007). No blocking requirements findings remain. No implementation started during this review.

- **B1–B3 remain resolved:** owner-only full-history path, source/output isolation and disjointness; raw-only storage and manifest verification; evidence-backed corporate-action/distribution prerequisites.
- **B4 resolved:** only market event dates are partitioned. Attestation dates retain their values, satisfy their own coverage/check ordering, never enter build_dataset, and declarations are deliberately copied rather than included in the event partition assertion.
- **B5 resolved:** the detailed contract now promises atomic publication per dataset, holdout first/development last; caught failures roll back, interruption leftovers block retry and require owner recovery. The specified interruption/retry test matches that scope.
- **Five clarifications accepted:** distinct validated session counts with excluded instruments insufficient; corrected proposal examples; §7.1 build provenance; explicit proposal flags; partition and holdout_start in dataset_id, with a separate manifest_digest for provenance. The identity extension is appropriate because these fields define permitted use.

Independent standard-library checks (synthetic only):
- Weekdays 2018-01-01 through 2025-12-31: H=2021-12-31, 1,044 development and 1,044 holdout sessions.
- Starting 2019-01-01: 783 development and 1,044 holdout sessions, insufficient under 1,009.
- Explicit Feb-29 -> Feb-28 convention gives target/H 2024-02-28 for E=2028-02-29 on a weekday calendar.
- Canonical identity calculation with four synthetic file digests changes when either partition or holdout_start changes.
- `git diff f346031 abc2f47 -- src tests` is empty: builder, tests and fixtures unchanged.

These are requirements/arithmetic checks, not implementation tests. No full suite rerun for this documentation-only review. CI green is reported by Claude; it is not independently re-verified here.

Minor implementation notes, not blockers: the card's short Goal still says “published atomically”; interpret it as the explicit per-dataset guarantee in Output 4 and tidy that wording when implementing. Return manifest_digest as computed metadata alongside the written manifest, not as a self-referential field inside the bytes being hashed. Preserve the explicitly chosen Feb-29 convention even when the target year is also leap.

The IBKR API observation is recorded as owner-reported only; it does not establish D5 adequacy or authorize funding, broker access, or real-data import. Real use still requires the charter boundary and evidence declarations.

Next: owner merges PR #10 with the acceptance record incorporated, then implement T-007 against this accepted contract on its own branch and submit the exact implementation head for Claude's independent review. No merge, build, real data, holdout access or broker call performed in this re-review.


## T-007 v3 — Codex's re-review findings B4, B5 and clarifications resolved (Claude) — 2026-10-16

All accepted; resolutions appended to `docs/decisions/0007-raw-datasets-isolation-and-corporate-actions.md`. Data spec v1.2.1 and card v3 on `t-007-card` ([PR #10](https://github.com/emanueltadesse61-del/Trading-bot/pull/10)); the commit for re-check is named in the PR comment.

- **B4:** partition rules apply to market events only (price date, distribution ex-date, calendar session). Declaration dates are attestation dates: real values, exempt from partitioning, never passed to the builder, and `checked_on` ≥ `corporate_actions_none_through`. Declarations are copied to both partitions and excluded from the no-duplication assertion.
- **B5:** atomic publication per dataset (holdout first, development last); rollback on caught failures. After an interruption, a re-run refuses (`SPLIT_OUTPUT_EXISTS` / `SPLIT_STAGING_EXISTS`) and the owner cleans up. Acceptance includes an `os._exit` interruption and the retry.
- **Clarifications:**
  - valid closes are distinct sessions, and excluded instruments are insufficient;
  - the calendar is validated first;
  - proposal cases were recomputed: 2018–2025 weekdays → H 2021-12-31 with 1,044/1,044 sessions; from 2019 → 783 sessions, insufficient; leap E → 2024-02-28;
  - §7.1 sentence fixed;
  - `dataset_id` now includes `partition` and `holdout_start`, plus `manifest_digest` for provenance;
  - proposal-mode flags listed.
- **Owner IBKR API check (owner-reported, 2026-10-16; not yet in the feasibility matrix):**
  - the unfunded account's paper login, through IB Gateway in read-only mode, returned daily historical bars for VWRP (data from 2019-07-25) and IGLT (from 2006-12-04): 253 bars over the last year;
  - CSPX was the wrong (USD) line;
  - full-depth history, units, split adjustment and dividend history are still to be checked for D5.

## Codex T-007 v2 re-review — 2026-10-16 (resolved in `docs/decisions/0007`, v3)

T-007 v2 requirements re-review at **eb113a7237489a65b92816f455a763f5de0a56ae: Changes requested. No build started.**

## Original findings

- **B1:** the public/private import separation, required workspace list, source/file/output preflight, filesystem-identity checks and disjoint/nonexistent outputs resolve the original boundary objections. Publication still needs the clarification in B5 below.
- **B2:** raw-only storage, explicit RawDataset metadata, exact five-file layout, named content hashes, recomputed summaries and error taxonomy resolve the original storage ambiguity. The newly added declaration dates conflict with the partition rule (B4 below).
- **B3: resolved.** The false split-detector claim is removed. Required evidence-backed declarations, complete distributions and rejection of unsupported corporate actions establish an explicit real-use prerequisite. This validates the contract, not any actual feed.
- Both design answers are adopted correctly: content identity over named files, and one owner-facing command.
- PR #9 merge is present in this branch. Source and tests/fixtures are unchanged against main f346031.

## B4 — Blocking: copied declarations cannot satisfy the partition/date rules

Locations: card Outputs 2 and 4 step 5; spec §8.4 validation step 4 and §8.5.

The owner command copies declarations to both partitions, but the reader requires **every dated row in every file** to be before H for development. A valid full-history declaration has corporate_actions_none_through >= the last holdout record, hence >= H, so the development read-back must reject it. Example: H=2022-10-17, last record=2026-10-16, corporate_actions_none_through=2026-10-16; the same declaration cannot pass both partitions. checked_on has the same issue for a recent check. Public import also rejects dates in “any file,” so a legitimate older development export checked today is rejected.

Define partitioned event dates explicitly (price date, distribution ex_date, calendar session), and give declaration coverage/check dates a separate provenance rule. Preserve their real values; do not backdate them to pass the cutoff. State that copied declarations are not included in the no-duplication partition assertion; market records/calendar partition exactly, declarations are intentionally copied. Add a round-trip case with an after-H check/coverage date and pre-H development prices, plus the existing rejection of a genuine on-H market row. Clarify that these are later source-quality attestations, not information available at historical t.

## B5 — Blocking: two renames do not meet the advertised crash guarantee

Locations: card Output 4 steps 6–7; spec §8.3.4; decision 0007.

Staging validates each individual output, but renaming holdout and then development is not a single atomic publication. If the process terminates after the first rename, no exception cleanup executes and the holdout directory remains. The reader's five-file contract accepts it independently. A minimal standard-library subprocess using os._exit(17) after the first rename leaves holdout present and development absent. Thus “a failed or incomplete run publishes nothing usable” and “no usable dataset is ever left behind” are stronger than the specified algorithm.

Choose one explicit contract before implementation:
- Narrow the guarantee to atomic publication **per dataset**, rollback for caught failures, and documented owner recovery for interruption/orphaned output; retain development-last ordering. The remaining isolated holdout is not itself a leakage failure.
- Or require a durable pair-commit/recovery protocol that readers enforce, with interrupted publication never considered a committed pair.

I recommend the first for this solo project; do not add a transaction system solely to preserve an overstatement. Add an interruption/retry acceptance case matching the chosen contract, alongside the handled-exception cleanup case.

## Small clarifications to include in the amendment

1. Output 5 needs a definition of “valid closes”: count distinct on-calendar sessions with finite positive prices, supported units and no invalid/duplicate price record under the existing validation rules. Counting raw duplicate rows can falsely reach 1,009. Validate the calendar before using its last/first sessions.
2. The positive “synthetic 7-year history gives expected H” acceptance case cannot normally meet 1,009 development sessions after reserving four years: only about three years remain. Use a sufficiently long synthetic session calendar for the success case; keep seven years as insufficiency, or explicitly lower min_dev_sessions for that isolated date-arithmetic test.
3. §7.1 still says the dataset manifest records exceptions provenance, whereas amended §8.1 correctly puts it in build/run provenance. Update that one sentence to remove the obsolete manifest requirement; this need not change builder behaviour or fixtures.
4. The content id excludes partition/H and other manifest provenance by design. A run must pin the manifest revision/digest or independently pin H/partition as well as dataset_id if those metadata are to be protected; dataset_id alone only pins the four Parquet files.
5. The proposal command should state which otherwise-required output/H flags are omitted in proposal mode, so the owner can calculate H before supplying H.

Evidence: exact-commit document and diff review; no source or fixture changes. Standard-library synthetic date comparison reproduced B4. A temporary subprocess with dummy staging directories reproduced the interrupted-rename state for B5; it did not exercise a T-007 implementation (none exists). No full suite rerun for this documentation-only review; no real data, broker access or holdout access. No strategy settings changed. Amend the card/spec/decision record and return for re-check.


## T-007 v2 — Codex's requirements findings resolved (Claude) — 2026-10-16

All three blocking findings and the clarifications are accepted and resolved in `docs/decisions/0007-raw-datasets-isolation-and-corporate-actions.md`. Branch `t-007-card` ([PR #10](https://github.com/emanueltadesse61-del/Trading-bot/pull/10)); the commit for re-review is named in the PR comment.

- **B1:** two import paths. The public `import_csv` refuses a missing holdout start (`IMPORT_HOLDOUT_REQUIRED`); only `trader-split` uses the private full-history parser.
  - Preflight runs before any read. It guards the source directory, every resolved input file and the holdout output, and requires source, dev and holdout locations to be disjoint by text and by identity.
  - Existing outputs are refused, and at least one workspace is required.
  - Publishing is staged, verified and atomic. Preflight tests prove refusal using a source that would fail to parse.
- **B2:** T-007 stores raw imports only. Spec §8.1 separates the raw-dataset manifest from build provenance (run registry, T-008).
  - §8.4 fixes the five-file layout, the `dataset_id` canonical JSON over four Parquet files, and the manifest fields.
  - Validation on read re-derives every summary and applies the partition rules to every row.
  - Empty partitions are refused. The limitation is stated: integrity, not authenticity.
- **B3:** my split-detection claim was wrong (4:3 gives exactly −25%, which is not flagged). Real use is gated by per-instrument owner declarations (§8.5).
- **Clarifications:**
  - Holdout proposal rule: E is the last session; H is the first session ≥ E − 4 calendar years; ≥ 1,009 development closes per instrument; insufficiency gives a report, never a shorter holdout.
  - `distributions.csv` is required, plus a completeness declaration.
  - Codes are named; the stale approval text is removed.
- Data spec §1–7, §9 and the fixture are unchanged.

## Codex T-007 requirements review — 2026-10-16 (resolved in `docs/decisions/0007`)

Requirements review at 9b534c96097910ccdd6778917dba9146ef9e1b99: **Changes requested; T-007 is not accepted and no build has started.**

N2 (INVALID_MODE) and N3 (typed CSV validation) are included. IBKR approval on 2026-10-16 is recorded; Table A remains owner-performed input to D5, not funding or broker-access permission.

## Answers to the two questions

1. Use a content identity: SHA-256 over canonical UTF-8 JSON containing a schema/version and a filename-keyed mapping of all three file SHA-256 digests. Specify JSON canonicalisation exactly. Do not hash an unlabelled sorted list of digests (it loses file identity), and do not include retrieval time, source label or code commit in the content id. Keep those in the provenance manifest; pin that manifest separately by its committed revision or digest when a run uses it. Same bytes can have the same dataset_id while having different provenance. Byte identity is guaranteed only under the pinned writer/schema settings; it is not a promise across arbitrary PyArrow versions.
2. One owner-facing command: trader-split performs parse, validation, split and writes both outputs. Keep parsing/splitting as independently testable internals. No second intermediate full-history Parquet dataset is needed. The existing source CSV export still exists, so one command does not remove the need to isolate and guard it.

## Blocking findings

**B1 — Owner import contract contradicts itself and omits the raw-source boundary (Outputs 1/3; data spec §8.3).**
import_csv refuses holdout_start=None for non-synthetic data, but trader-split is required to do exactly that. Also, only holdout_out is guarded: a source inside an agent workspace passes the specified preflight when the output is elsewhere, contrary to §8.3. Define a private full-history parsing path used by the owner command, while retaining the public development-import refusal. Before reading content, guard the source directory and resolved input files as well as holdout_out against repo/all workspace roots (including symlink aliases). Require source/dev/holdout destinations to be disjoint, including ancestor relationships and filesystem aliases: dev_out=holdout_out otherwise writes one partition over the other before verification. Specify failure behaviour so incomplete or failed output is not returned/published as a usable dataset. Add synthetic preflight cases with an unreadable source, a forbidden source, symlinked source file, and overlapping outputs. A CLI warning is not an isolation check; the owner-only execution rule still applies.

**B2 — Storage contract does not satisfy its named spec and leaves round-trip metadata undefined (Output 2; spec §§7.1/8.1).**
§8.1 requires built series, calendar reference and exceptions provenance; the proposed API only receives raw ImportResult and writes three raw-record files, with no mode/version/digest. Decide explicitly whether T-007 stores raw imports only (with a spec amendment and a separately defined later built-dataset manifest) or also persists builds and their provenance now. Do not fabricate exceptions provenance for raw data. Define ImportResult fields carrying holdout_start/synthetic status, and how split outputs preserve them; write_dataset has no other source for these manifest fields. Specify validation of schema, exact required file set, recomputed dataset_id, date range and instrument metadata, and development cutoff rather than trusting the JSON summaries. E.g. changing date_range.last to an earlier date currently evades the listed file/count checks and undermines the split's manifest-only boundary verification. Define empty-partition behaviour and whether manifest.json is allowed inside data_dir (the CLI writes manifests to output directories, while the reader rejects extra files). Add cases for metadata tampering and empty partitions. Hash checks provide integrity against a pinned manifest, not authenticity if both files and manifest can be replaced.

**B3 — The corporate-action limitation relies on a false detection claim (Constraints; data spec §10).**
For a pure r:1 split, price drop is 1-1/r. Exact Fraction calculations give 1.33:1 -> 24.812030075%, and 4:3 -> exactly 25%; neither exceeds the existing strict >25% JUMP_LIMIT. A 1.2:1 split drops 16.6667%, and market moves can also mask larger splits. Remove the claim that these actions are reliably caught. Keeping split adjustment out of scope is fine, but explicitly gate real use on dated source/owner evidence for corporate-action coverage and supported price semantics, or mark that instrument unusable until supported. The jump flag is an anomaly check, not proof that no split occurred. Retain the prohibition on approving a split-induced jump as ordinary cleaning.

## Clarifications / real-use prerequisites

- The holdout proposal avoids event selection, which is correct, but “latest session such that ... usable data for both periods” does not uniquely define four years or a minimum development span. Before real import, pin an as-of end session, calendar-year subtraction/session-boundary convention, and minimum development/warm-up sufficiency. Insufficient history should return a feasibility decision, not silently shorten the holdout. Actual dates remain the owner's decision; no dates chosen here.
- Absent distributions.csv currently means confirmed zero payments. A missing export for a distributing fund would silently turn total returns into price returns. Require an explicit completeness/no-payments declaration before real use; a missing file alone is not evidence.
- Remove stale “account approval pending” from the card and PR description. Account approval does not establish D5 adequacy.
- Name the no-holdout-date refusal code, and define missing files/malformed CSV handling. These are small boundary-contract additions, not strategy changes.

Evidence: read the exact card, charter/handoff and data-spec storage/isolation/provenance requirements against the existing record classes, builder and guard. Independently evaluated the three split ratios with Python Fraction; all are below or equal to the strict jump threshold. This is a requirements review, not a test of a new implementation; no new code or real data was run. Claude should amend the card/spec and record material resolutions before re-review.


Last updated: 2026-10-16 by Claude. Update this file at the end of every session (`AGENTS.md`).

## Current phase

**Phase 0 — feasibility.** No real money, no account funding, no purchases authorised (`docs/charter.md` §2).

## Review target

Roles are back to `AGENTS.md`: **Claude specifies and reviews; Codex checks specs and builds.**

| Item | Value |
|---|---|
| T-005 | [PR #7](https://github.com/emanueltadesse61-del/Trading-bot/pull/7): v1 reviewed at `3dceea8` (B1 holdout, B2 jump-approval timing); v1.1 resolves both (decision 0006). Re-review commit named in the PR. Reviewer: Codex |
| Merged | PR #1 `c1ae73d`; PR #2 `5ec568f`; PR #3 `489eda8`; PR #4 `96df2b0`; PR #5 `3ba0728`; PR #7 `450fc3f`; PR #8 `98d3bb4`; PR #9 `f346031` (each pinned to the accepted commit). PR #6 closed by the owner |
| Merged (cont.) | PR #10 `7aad2a9` (T-007 v3 + data spec v1.2.1; Accepted by Codex at `abc2f47`) |
| Open | Owner-decisions PR (decision 0008): Codex consistency check |

## Decisions

**Confirmed** (owner, decision 0008 unless noted): 10 strategy instruments with SGLN as the one non-UCITS exception, plus VWRL benchmark-only (11 data instruments), GBP-hedged Treasuries dropped; 3 of 20 variants reserved, 0 run; 3/6/12 lookbacks primary with 1/3/12 robustness variant; weekly rebalancing primary with monthly robustness variant; stop rule checkpoint Mon 2027-03-08 (calendar weeks from 2026-10-19); £600/year ceiling (cap, not approval); paper-first; 4-year holdout by the T-007 rule. Earlier: UK residence; IBKR account approved 2026-10-16 (no funding authorised); Phase 0 then gated development and paper trading; £0 real capital; no purchases without approval; no LLM signals; trial history never reset; an inspected holdout is consumed; time commitment flexible in bounded weekly milestones.

**Proposed defaults** (in force until the owner changes them): £10,000 simulated paper balance; paper pause at 15% and stop at 25% below peak equity; GBP lines only; 60/40 deciding benchmark; Gate 3 rule in `docs/research-protocol.md` §6; trial budget 20.

**Pending** (owner decides):
1. D5 data source, after the owner's full-history IBKR check across all 11 data instruments (10 strategy + VWRL): depth, units, split adjustment of `TRADES` bars, distribution history.
2. Confirm each instrument has ≈ 8 years of history; several inception dates are UNVERIFIED.
3. `declarations.csv` evidence (data spec §8.5), once D5 is settled.
4. The exact holdout date: owner-only proposal → charter confirmation → split, before development data enters any agent location.

## Tasks

| Task | State | Owner of next step |
|---|---|---|
| T-001 Repository bootstrap | **Merged** (`c1ae73d`) | — |
| T-002 Portfolio spec + reference cases | **Merged** (`5ec568f`) | — |
| T-003 Portfolio engine | **Merged** (`489eda8`; Accepted at `a783e0c`) | — |
| T-004 Feasibility matrix | **Merged** (`96df2b0`; Accepted at `2f31a6b`); D1, D2 decided (0008) | Owner: Table A checks, D5 |
| Research library | **Merged** (`3ba0728`; Accepted at `55d3dad`); R-002, R-006 decided (0008) | — |
| T-005 Data-layer spec + reference cases | **Merged** at `450fc3f` (spec accepted at `619de06`) | — |
| T-006 Data build + holdout guard | **Merged** (`98d3bb4`; Accepted by Claude at `85087b6`) | — |
| Data spec v1.1.1 (N1 duplicate wording) | **Merged** (`f346031`; Accepted by Codex at `f0982fb`) | — |
| T-007 Storage, CSV import, owner-run split | **Implemented** in PR #12; **accepted by Claude at `eceba59`** (card merged `7aad2a9`) | Owner merges PR #12 |

Planned after T-007: T-008 backtest simulator, cost model and baselines (synthetic data first; extends the data spec with next-session open prices); a broker adapter (IBKR) after account approval.

Cards: `docs/tasks/`. Copy each into a GitHub issue when convenient; the files remain the reference until then.

## Completed

| Item | Commit | Evidence |
|---|---|---|
| Bootstrap documents, templates, task cards | `c949dfd` | Files listed below |
| T-002 deliverables (Claude) | `c949dfd` | Reference values computed by Claude's own calculator, kept outside the repo |
| T-001 review (Claude) | `3332ccd` | [Review on PR #1](https://github.com/emanueltadesse61-del/Trading-bot/pull/1#pullrequestreview-5541923875) |
| T-002 v1.1: spec, protocol §6, fixture (26 cases), decision 0002 | branch `t-002-spec-fixes` | `docs/decisions/0002-t002-review-resolutions.md` |
| T-002 v1.2: B5 variance numerics (spec §2.2), W8, V9, T-002 card cleanup | branch `t-002-spec-fixes` | `docs/decisions/0003-portfolio-volatility-numerics.md`; 28 cases; all 26 earlier cases unchanged value-for-value |

Bootstrap files: `AGENTS.md`, `CLAUDE.md`, `docs/charter.md`, `docs/architecture.md`, `docs/research-protocol.md`, `docs/portfolio-spec.md`, `docs/portfolio-reference-cases.md`, `docs/decisions/0001-record-decisions.md`, `docs/tasks/T-001…T-004`, `.github/ISSUE_TEMPLATE/task-card.md`, `.github/pull_request_template.md`, `tests/fixtures/portfolio_cases.json`.

## Checks

**Historical bootstrap checks (10 cases at v1; current v1.2 has 28)**
- Fixture loads and contains 10 cases: `python3 -c "import json; d=json.load(open('tests/fixtures/portfolio_cases.json')); print(len(d['weights'])+len(d['orders'])+len(d['signals']))"` → `10`.
- W1 and O1 hand-checked against the calculator (working in `docs/portfolio-reference-cases.md`).

**Completed by Codex**
- W1, W4, O1, O2 independently reproduced; details below.
- `uv sync --locked && uv run ruff check . && uv run pytest -q`: passed, 28 tests.
- GitHub CI passed on implementation commit `ba5e40e68eedd45b0230681bf833d2e808cf273a`: [run 38835035359](https://github.com/emanueltadesse61-del/Trading-bot/actions/runs/38835035359).

**Completed by Claude (T-002 v1.1)**
- Fixture regenerated with Claude's independent calculator (outside the repo): 7 weight, 10 order, 1 signal and 8 invalid-input cases; strict JSON (`allow_nan=False`).
- All v1 expected weights and orders unchanged. Only O1 `k`/`buy_need` and O2 `buy_need` moved, because of the commission reserve.
- `tests/unit/test_smoke.py` fixture-name list updated for the new cases and passes. Claude's workspace can't reach PyPI, so the full `uv` run is left to CI on the T-002 PR.

**Pending**
- Owner merges PR #1, then accepted PR #2. No specification blockers remain from this review.

## Blockers

- IBKR account **approved 2026-10-16**. T-004 Table A checks are now the owner's to perform on the owner's own machine (agents never touch the broker or credentials). Results go into `docs/feasibility-matrix.md` with dated evidence.
- None for Claude: GitHub is linked and Claude can push.

## Next

1. Owner: merge PR #12 (T-007, accepted by Claude at `eceba59`). Do not start another T-007 build.
2. Codex: consistency check of decision 0008 on the owner-decisions PR.
3. Owner: full-history IBKR check across the 11 data instruments, which feeds D5. Then the declarations; then the holdout proposal → charter confirmation → split.

## Codex T-002 review — 2026-10-16 (resolved in `docs/decisions/0002`)

Review base: `c949dfd5a9bdd16007025206415d51101406a2a3`; checkout base `8b7d331` adds only the handoff SHA. No spec or fixture changes made. T-002 is **Changes requested**, not Accepted. Findings do not block the independent empty T-001 skeleton.

### Blocking findings

1. **B1 — contradictory all-ineligible outcome (portfolio spec §§3, 6, 7).** §7 says no eligible instruments causes existing holdings to exit. §§3/6 instead block any held ineligible instrument, and architecture §1 prohibits selling on bad data. Example: one held ETF loses its latest close and U becomes empty: the two rules prescribe a sale and no orders respectively. Make the precedence explicit; distinguish eligible instruments with zero signals from an empty eligible universe. Add a reference case.
2. **B2 — calendar/date contract missing (portfolio spec §§2–3).** Right-aligning arrays on their last element cannot establish consecutive sessions ending at t. Example: A has Monday–Friday closes, B has 253 observations ending Thursday after a Friday outage; right alignment silently treats Thursday as Friday. Define a shared dated calendar/mask or require and test a validated aligned-input contract that preserves missing sessions before the pure signal function runs. Current undated fixtures cannot verify this property.
3. **B3 — invalid numeric inputs lack defined outcomes (portfolio spec §§2–6).** Define finite, strictly positive prices; finite nonnegative cash and integral nonnegative holdings; positive NAV; consistent IDs/dimensions; finite symmetric valid covariance; and explicit rejection outcomes at the responsible boundary. Example: empty unfunded account gives NAV=0; P=0 divides by zero; NaN volatility can evade ordinary comparison checks. “Data checks passed” does not define these account/math preconditions. Do not invent behaviour in T-003.
4. **B4 — Gate 3 outcome overlap (research protocol §6).** The simpler-rule test explicitly says failure if its Sharpe advantage is below .10, but the Inconclusive rule includes every positive benchmark ΔSR short of pass bars before holdout. Example: ΔSR=.30, bootstrap=.90, acceptable drawdown/cost stress, but simpler-rule advantage=.05: both Fail and Inconclusive apply. Specify outcome precedence and which shortfalls permit prospective continuation. This is a protocol blocker, not a blocker to T-001.

### Non-blocking follow-ups

- **N1 — fees and execution revalidation (portfolio spec §6.5–6.6).** A 0.5% price buffer is not an explicit commission reservation; costs are excluded from projected NAV. A £100 order with £100.50 cash and £1 commission can exceed cash even at the reference price. Before broker integration, specify fee-aware, fresh-price risk checks; the current planner is a reference-price approximation, not execution approval.
- **N2 — fixture coverage.** Add cases for missing sessions, invalid numeric input, no eligible assets, and an unresolved constraint after repair when amending the spec. Current examples validate ordinary arithmetic, not every failure branch.

### Independently reproduced calculations

A temporary standard-library calculator outside the repository (`/tmp/review_trading_t002.py`) read only synthetic fixture inputs and compared calculations with the recorded expectations at absolute tolerance 1e-8. Command: `python3 /tmp/review_trading_t002.py` — passed.

- W1: pre-scale volatility 0.09334380331881288; scale 1; all recorded weight-stage values match.
- W4: pre-scale volatility 0.1676054214305116; scale 0.5966394114611592; all recorded weight-stage values match.
- Additional W2, W3, W5 weight-stage values also match.
- O1: independently recomputed targets give SELL BD_GILT 10, GOLD 8; BUY EQ_JP 34, EQ_US 8; buffered unscaled buy need £1507.50.
- O2: initial BUY EQ4 60 implies class weight .657; repair sells EQ1–EQ3 19 each, retains BUY EQ4 60; buffered buy need £603.
- No historical backtest, market data, broker calls, or experiment variants were run. Signal fixture arithmetic and every order diagnostic were not independently reproduced in this review.

## T-001 implementation evidence

Branch: `t-001-bootstrap`. Implementation commit: `ba5e40e68eedd45b0230681bf833d2e808cf273a`. PR: https://github.com/emanueltadesse61-del/Trading-bot/pull/1. The PR names the final review head (including this handoff update).

Added Python 3.12 src-layout package with nine empty components, uv lockfile, NumPy/pandas runtime dependencies, pytest/ruff development dependencies, CI, README, ignore rules, import/fixture smoke tests, and static import/live-config guards. No strategy implementation or fixtures changed.

Completed locally: `uv sync --locked`, `uv run ruff check .`, `uv run pytest -q` (using uv 0.13.1 and Python 3.12.15). The parametrised forbidden-import tests exercise both SDKs, aliases, from-imports, submodules and nested imports. Static import checks are not a security sandbox.

CI: implementation commit passed on GitHub Ubuntu (run 38835035359). Final handoff-only revision will be checked and its result recorded in PR #1. Owner merge and Claude review remain required.

## Codex v1.1 re-review — 2026-10-16

**Reviewed exact revision:** `c457ca55448cd46cace5c64a39cc3f9c687256ab` (PR #2). B1, B2, B3 and B4 are resolved for their reported scenarios; N1's commission-reserve scope and N2's added coverage are accepted. One newly introduced numerical boundary needs a defined outcome. T-002 remains **Changes requested**; no T-003 implementation started. PR #1 was still open/unmerged when checked.

### B5 — Blocking: tolerated covariance can produce undefined volatility

**Sections:** portfolio spec §2.1 (`PSD_TOL`) and §5.6 / §6.3 (quadratic-form square roots).

The validity rule accepts a smallest eigenvalue as low as −1e-12, but the downstream formula unconditionally evaluates `sqrt(w.T @ cov @ w)`. An accepted input can therefore have no real-valued result. Example: two assets, covariance `[[0.04, -0.0400000000005], [-0.0400000000005, 0.04]]`, weights `[0.25, 0.25]`. The smallest eigenvalue is approximately −5e-13 (within tolerance), while variance is approximately −6.25e-14. Both diagonal variances are positive; direct square root fails. A still smaller one-asset counterexample is covariance `[[-5e-13]]`, weight .25: accepted eigenvalue, variance −3.125e-14, `math.sqrt` raises `ValueError`.

**Requested resolution:** define one consistent tolerance-safe volatility calculation for targets and both planner checks (for example, after covariance validity checks, symmetrise within the permitted asymmetry and clamp tolerated negative quadratic-form roundoff to zero), or reject all negative eigenvalues and revise the tolerance rule. State the chosen policy in the decision record and add a boundary reference case. Codex has not chosen or implemented the policy.

### Non-blocking documentation cleanup

T-002's task card still describes 5/4/1 fixtures and old subsection numbers, while v1.1 has 7 weight, 10 order, 1 signal and 8 invalid-input cases. The handoff's earlier 10-case load entry is historical, not a current count. Update these labels during the amendment; no fixture result depends on them.

### Independent reproduction and checks

Temporary calculation script outside the repository: `/tmp/review_t002_v11.py`; command `python3 /tmp/review_t002_v11.py` passed all assertions, then reproduced B5 with a caught square-root domain error. Only synthetic fixtures were used.

- S1: 253 distinct ordered dates; STALE is missing at index 252 (decision date), GAP at index 100. Both independently classify as `missing_data`. SHORT has leading missing values 0–52 and is `insufficient_history`. All three eligible series' returns, trend scores, momentum, volatility, and the entire annualised covariance matrix match within 1e-8.
- O7: empty eligible set and held P -> `BLOCKED_HELD_INELIGIBLE`; no sale.
- O9: NAV £10,000; proposed Y buy 250 shares; buffered need plus reserve £2,515.50; settled cash zero -> k=0. Actual X weight .25 has volatility .125; Y is already in S, so nothing new can be added -> `BLOCKED_CONSTRAINTS` after one pass, no orders.
- V2: covariance asymmetry 1e-6 > SYM_TOL 1e-12 -> `INVALID_COVARIANCE`.
- `uv sync --locked --offline`: passed using cached dependencies.
- `uv run --offline ruff check .`: all checks passed.
- `uv run --offline pytest -q`: 28 passed. These are skeleton/guard/fixture-name tests; no trading implementation exists yet.
- GitHub CI on c457ca5: push run 38835875431 and PR run 38835897171 both succeeded.

Specs, reference fixtures, and source code unchanged by this review. The only repository edit is this handoff update; the PR comment records the reviewed spec SHA separately from the handoff commit. No orders, real data, holdout access, purchases, merge or deployment.

## Codex v1.2 acceptance — 2026-10-16

**T-002 Accepted.** Reviewed specification revision: `4d4bc9359e97ccb55e0aaafa8a6900e907b2b242` in PR #2. B5 is resolved by decision 0003 and spec §2.2. No blocking findings remain. The target calculation (§5 step 6), actual-portfolio check (§6.3 step 3) and post-trade check (§6.3 step 6) all reference the shared volatility rule; zero volatility explicitly skips scaling. Materially invalid covariance still fails validation rather than being hidden by clamping.

Independent calculator: `/tmp/review_t002_v12.py`, outside the repository. Command: `python3 /tmp/review_t002_v12.py`. Used the analytic eigenvalue formula for a symmetric 2x2 matrix and direct quadratic-form summation, independent of Claude's calculator.

- W8: minimum eigenvalue −4.999958780338432e-13; variance −6.24994847542304e-14; accepted within tolerance, volatility 0, scale 1, weights .25/.25, cash .50. Matches fixture.
- V9: minimum eigenvalue −1.000000082740371e-11, below −1e-12; `INVALID_COVARIANCE`. Matches fixture.
- Compared all 26 pre-existing fixture cases against c457ca5: unchanged, including inputs, expectations and descriptions. Two cases added; total now 28.
- `uv sync --locked --offline`: passed.
- `uv run --offline ruff check .`: all checks passed.
- `uv run --offline pytest -q`: 28 passed. These remain skeleton/guard/fixture-list checks, not an implemented strategy test suite.
- GitHub CI on the exact reviewed revision: push run 38836464917 and PR run 38836469395 both succeeded.

Only this handoff was edited for acceptance; no spec, fixture or source changes. PR #1 and PR #2 remained open/unmerged at review time. T-003 has not started and remains blocked by the T-001 merge prerequisite. Owner should merge PR #1 then PR #2; acceptance does not authorise trading, spending, deployment or an agent merge.


## Codex T-005 review — 2026-10-16 (resolved in `docs/decisions/0006`)

Codex T-005 review at **3dceea8e70071105dca3411fa61a9bd8c4c0c114: Changes requested.** T-006 remains Draft; no implementation started.

### Blocking

**B1 — Holdout containment is weaker than the existing protocol (§8, D14, T-006 holdout signature).** Research protocol §3 and AGENTS.md require exclusion from the repo AND every agent workspace. D14 accepts /work/Trading-bot-holdout because it is outside /work/Trading-bot, but if the agent workspace is /work the data is still inside it. The two-argument guard cannot establish the stronger property. The split/write description also needs to say who runs it and where raw holdout records are first read, so a local full-history import does not expose the holdout before splitting. Either define this explicitly as a limited repo-containment primitive and add a separate mandatory owner-run isolation boundary before any real-data ingestion, or extend the forbidden-root contract and cases. Do not imply that passing D14 authorises holdout storage/access. This is enforcing the existing no-agent-workspace rule, not requiring a fully separate evaluation platform.

**B2 — Jump approval time has no defined effect (§7, D6, research protocol §4).** D6 has t=2026-01-09 and approval=2026-10-16, yet data_ok=true. This is reproducible under the membership-only rule, but later approvals can retrospectively change whether an earlier run trades. Decide explicitly between (a) as-of operational approval, which must exist by t, and (b) a frozen, versioned research-cleaning snapshot approved before the evaluation, whose later date is permitted but is not represented as information available at t. State how the relevant snapshot is selected and pinned, and what happens for missing/malformed approval dates or empty reasons. Record its hash/version in the dataset/run provenance. Add cases for a future approval and an approval absent from the selected snapshot. Without this distinction the builder's behaviour and the leakage guarantee cannot both be judged.

### Non-blocking clarifications to address with the amendment

- §3 and the T-005 choices table say a held record-error instrument produces BLOCKED_HELD_INELIGIBLE. In the accepted planner, data_ok=false is checked first and produces BLOCKED_DATA, even when the bad instrument is unheld. Both prevent unsafe sales; align the documented status and global blocking scope with the existing engine, and add a composition test. Stale-only inputs can still use the held-ineligible path.
- §7 calls JUMP_LIMIT a 'one-session' threshold but compares consecutive valid prices across gaps. 100, None, 130 is a 30% multi-session move and is flagged under the written formula. Choose/document that behaviour and add a gap-jump case; do not silently invent daily interpolation.
- Define build-boundary handling of duplicate/unsorted/empty calendars, unknown record ids and records before the supplied calendar range. T-006 currently only pins t-not-in-calendar. Also retain approved jump provenance in the audit report or manifest even if the active DATA_JUMP flag is suppressed.
- Splits, next-open execution prices and non-GBP distribution amounts remain real-adapter/backtester prerequisites, not solved by this close-only synthetic contract; their deferral is acceptable if T-007/T-008 gate their use.

### Independent reproduction

Temporary standard-library calculator outside the repo: /tmp/review_t005.py; command python3 /tmp/review_t005.py. Used exact Fraction arithmetic and reinvested-share accounting rather than copying the proposed chained-return implementation.

- D2: 100, 100, 102.02020202020202, 101.01010101010101, 103.03030303030303.
- D3: 100, 102, None, 106, 104.98076923076923.
- D7: A all None, DATA_OFF_CALENDAR on 2026-01-03; B 50,51,52,53,54; data_ok=false.
- D11: output stops at Jan 8; A all None, DATA_FUTURE_RECORD on Jan 9; B 50,51,52,53; data_ok=false. Future price is on the supplied calendar, so it is not also off-calendar.
- D12: 20,20.05,20.251507537688443,20.352261306532665,20.201130653266333; trade_close=20.05.
- D14: both repository paths refused; both outside paths accepted, matching the fixture's limited containment rule. This did not test an implemented guard or access actual holdout data.

All requested expected fields match within 1e-10, with exact statuses/reports. Existing suite: 575 passed under Python 3.12; ruff passed. These tests cover the existing portfolio engine, not a built data layer. Both CI checks on the reviewed SHA succeeded (38887131737, 38887101247). No code, spec or fixture edits, market-data downloads, broker access, holdout access, experiments, spending or merges. Claude should resolve B1/B2 in the spec/decision record before T-006 becomes Ready.


## Codex T-005 v1.1 acceptance — 2026-10-16

Codex re-review: **T-005 v1.1 Accepted at 619de06e32a046fc15e8f2c4f9f37f84a884d6d9.** B1/B2 are resolved by decision 0006 and spec §§7.1, 8.2–8.3. Containment now includes every supplied agent workspace root; the guard is explicitly limited, and owner-run import/splitting keeps holdout records out of agent datasets. Operational approvals are as-of t; research uses an explicitly frozen pre-evaluation snapshot with recorded provenance. The smaller status, gap-jump, calendar and deferred-adapter clarifications are incorporated.

Independent standard-library reproduction outside the repo: `python3 /tmp/review_t005_v11.py` passed. D6 reports DATA_JUMP_APPROVED in research; D6b keeps DATA_JUMP for a future operational approval; D6d reports DATA_INVALID_EXCEPTION plus DATA_JUMP; D15 flags the 30% gap-spanning move. D14 matches all six literal paths, including rejection of the repo sibling within /work and acceptance of /work2. DV5 gives INVALID_EXCEPTIONS_VERSION by the specified contract. D14/DV5 are independent contract checks, not tests of an implemented data layer or runtime symlink handling.

Recomputed canonical JSON digests: D6/D6b `c0d216361c0192af1a10e06caf3db3d16f853da9f8da2634f7739b62b60617e1`; D6d `44e4cdc8b445dd3bb89dc41592425e5bbbcba1435587a1641bfe01d1558c28d4`; empty list `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`. All match. Compared the 12 unaffected original cases' expected fields against v1: unchanged; fixture now has 26 cases.

Existing suite: genuine Python 3.12 pytest, 575 passed; ruff passed. Both CI runs on the exact SHA succeeded (38887823632, 38887817188). These are existing-engine checks, not proof that T-006 exists. No blocking findings remain. T-006 becomes Ready; no implementation started in this review. No spec/fixture/source changes, real-data download, holdout access, broker call, experiment, purchase or merge into the project branch. Owner retains merge authority.

## T-006 implementation — 2026-10-16

Branch `t-006-data-build`, based on latest main `450fc3f` (PR #7 merged with the accepted spec and acceptance handoff). Exact review head and CI links are recorded in the PR.

Implemented canonical frozen records, data-quality defaults, pure build_dataset, and the resolved-path holdout containment guard. The builder validates records in spec order, converts units, preserves missing sessions, constructs distribution-adjusted closes, reports jump/stale/error conditions, and records operational/research exception provenance with the canonical SHA-256 digest. The guard rejects repo/workspace descendants including symlink aliases and does not create files.

Local checks: `PYTHONPATH=src /tmp/trading-bot-codex/.venv/bin/python -m pytest -q` → **622 passed** under Python 3.12; `/tmp/trading-bot-codex/.venv/bin/ruff check .` → passed; `git diff --check` → passed. All 26 data fixture cases pass unchanged (including DV1–DV5), plus both required engine composition tests. Added tests for empty/no-record universes, malformed numeric inputs, validation precedence, cutoff behaviour, exception timing/digests, frozen defaults, valid integration, nonmutation, and symlink/root containment. Specs and fixtures are unchanged against main. Implementation commit `b73a24d6aaf95dbf2f9ffe8ef08bb70e5eba73ca` passed both GitHub CI runs: [push 38889037917](https://github.com/emanueltadesse61-del/Trading-bot/actions/runs/38889037917) and [PR 38889083454](https://github.com/emanueltadesse61-del/Trading-bot/actions/runs/38889083454). [PR #8](https://github.com/emanueltadesse61-del/Trading-bot/pull/8) records the final review head, including this evidence-only handoff update, and its CI result.

Routine interface choices: canonical record/session dates use datetime.date; approval dates remain ISO strings so malformed approvals can be reported. Invalid mode values (outside the two specified modes) raise ValueError; missing/blank research versions raise INVALID_EXCEPTIONS_VERSION. Identical issue triples are emitted once, matching duplicate-record fixture reporting. Defaults use a read-only units map. The guard uses Path.resolve and does not claim to prevent later filesystem changes or authorise holdout access.

Data: synthetic only; no experiments. No new dependencies, storage, downloads, real-feed adapter, broker calls, holdout access, funding, deployment or merges. The guard cannot discover omitted workspace roots; callers must supply all roots and enforce the owner-run boundary before real ingestion. Claude review remains outstanding.


## T-006 Claude review B1 fix — 2026-10-16

Reviewed implementation was `a43aefdb89b2a28a3e75795aec346929f12d4ca9`; Claude requested one guard correction in review 5551443923. The guard now retains resolved lexical containment and additionally calls os.path.samefile for the destination and each ancestor against every resolved forbidden root. Missing paths are skipped so nonexistent leaves are supported; other filesystem errors propagate rather than implying safety. No paths are created.

Regression coverage simulates case-insensitive identity for both repository and agent-workspace roots, includes nonexistent destination children and a permitted prefix sibling, and checks that access errors are not swallowed. Existing real symlink tests remain. Local Python 3.12 pytest: **625 passed**; ruff and git diff --check passed. Specs, fixtures and builder logic unchanged. CI for the exact fix commit is recorded in PR #8.

N1 remains Claude's spec clarification. N2 (mode error taxonomy) and N3 (typed-record adapter validation) are deferred to the adapter boundary rather than changing the accepted interface here. No new input-error code is introduced. T-006 remains Review pending Claude's re-check of B1. No merge, downloads, holdout access, broker calls or spending.
