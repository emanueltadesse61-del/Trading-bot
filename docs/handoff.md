# Handoff — read this first

Last updated: 2026-10-16 by Claude. Update this file at the end of every session (`AGENTS.md`).

## Current phase

**Phase 0 — feasibility.** No real money, no account funding, no purchases authorised (`docs/charter.md` §2).

## Review target

Roles are back to `AGENTS.md`: **Claude specifies and reviews; Codex checks specs and builds.**

| Item | Value |
|---|---|
| T-005 | [PR #7](https://github.com/emanueltadesse61-del/Trading-bot/pull/7): v1 reviewed at `3dceea8` (B1 holdout, B2 jump-approval timing); v1.1 resolves both (decision 0006). Re-review commit named in the PR. Reviewer: Codex |
| Merged | PR #1 `c1ae73d`; PR #2 `5ec568f`; PR #3 `489eda8`; PR #4 `96df2b0`; PR #5 `3ba0728` (each pinned to the accepted commit) |
| Open | PR #6 (Codex's T-003 review record): stays open until the owner authorises closing it |

## Decisions

**Confirmed** (owner): UK residence; new IBKR account being created; Phase 0 then gated development and paper trading; £0 real capital; no purchases without approval; no LLM signals; trial history never reset; an inspected holdout is consumed; time commitment flexible in bounded weekly milestones.

**Proposed defaults** (in force until the owner changes them): £10,000 simulated paper balance; paper pause at 15% and stop at 25% below peak equity; £600/year data-and-hosting ceiling; ~12 UCITS ETFs, GBP lines only; weekly rebalance; 60/40 deciding benchmark; Gate 3 rule in `docs/research-protocol.md` §6; trial budget 20; holdout 3–5 most recent years.

**Pending** (owner decides):
1. Research stop rule: week 20 counted in **calendar** weeks from an agreed start date, or in **worked** weeks logged here with a hard calendar cap. Also: the start date.
2. Confirm the £600/year ceiling and that paper-first suits you.
3. After T-004: which paid data, if any.

## Tasks

| Task | State | Owner of next step |
|---|---|---|
| T-001 Repository bootstrap | **Merged** (`c1ae73d`) | — |
| T-002 Portfolio spec + reference cases | **Merged** (`5ec568f`) | — |
| T-003 Portfolio engine | **Merged** (`489eda8`; Accepted at `a783e0c`) | — |
| T-004 Feasibility matrix | **Merged** (`96df2b0`; Accepted at `2f31a6b`); account rows **Blocked** | Owner: D1–D3 now; D5 and Table A after account approval |
| Research library | **Merged** (`3ba0728`; Accepted at `55d3dad`) | Owner: R-002, R-006 |
| T-005 Data-layer spec + reference cases | **Merged** at `450fc3f` (spec accepted at `619de06`) | — |
| T-006 Data build + holdout guard | **Review** | Claude reviews the exact T-006 PR commit |

Planned after T-006: T-007 storage, manifests and the first real-feed adapter (after feasibility D5); T-008 backtest simulator, cost model and baselines.

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

- IBKR account not yet approved → T-004 Table A blocked.
- None for Claude: GitHub is linked and Claude can push.

## Next

1. Claude: independently review T-006 at the exact SHA named in its PR, against data spec v1.1 and the unchanged fixture.
2. Owner retains merge authority. T-007 real-data work remains gated by holdout dates and feasibility checks.
3. PR #6 remains open; no closure authorised in this task.

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
