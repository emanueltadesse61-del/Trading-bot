# Handoff — read this first

Last updated: 2026-10-16 by Claude. Update this file at the end of every session (`AGENTS.md`).

## Current phase

**Phase 0 — feasibility.** No real money, no account funding, no purchases authorised (`docs/charter.md` §2).

## Review target

| Item | Value |
|---|---|
| T-001 | [PR #1](https://github.com/emanueltadesse61-del/Trading-bot/pull/1) at `3332ccd8ebce7479cc78aea471f58c905c362099`: Claude review posted, **no blocking findings**; awaiting owner merge |
| T-002 v1.1 | Branch `t-002-spec-fixes` (built on PR #1); exact commit named in its PR. Reviewer: Codex |

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
| T-001 Repository bootstrap | **Accepted** (Claude review: no blocking findings) | Owner merges PR #1 |
| T-002 Portfolio spec + reference cases | **Review** (v1.1: all findings resolved in `docs/decisions/0002`) | Codex re-checks v1.1, then Accepted or findings |
| T-003 Synthetic portfolio implementation | Draft (Ready when T-002 Accepted and T-001 merged) | — |
| T-004 Feasibility matrix | Ready (document); account rows **Blocked** | Codex drafts; owner does account checks |

Cards: `docs/tasks/`. Copy each into a GitHub issue when convenient; the files remain the reference until then.

## Completed

| Item | Commit | Evidence |
|---|---|---|
| Bootstrap documents, templates, task cards | `c949dfd` | Files listed below |
| T-002 deliverables (Claude) | `c949dfd` | Reference values computed by Claude's own calculator, kept outside the repo |
| T-001 review (Claude) | `3332ccd` | [Review on PR #1](https://github.com/emanueltadesse61-del/Trading-bot/pull/1#pullrequestreview-5541923875) |
| T-002 v1.1: spec, protocol §6, fixture (26 cases), decision 0002 | branch `t-002-spec-fixes` | `docs/decisions/0002-t002-review-resolutions.md` |

Bootstrap files: `AGENTS.md`, `CLAUDE.md`, `docs/charter.md`, `docs/architecture.md`, `docs/research-protocol.md`, `docs/portfolio-spec.md`, `docs/portfolio-reference-cases.md`, `docs/decisions/0001-record-decisions.md`, `docs/tasks/T-001…T-004`, `.github/ISSUE_TEMPLATE/task-card.md`, `.github/pull_request_template.md`, `tests/fixtures/portfolio_cases.json`.

## Checks

**Completed**
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
- Owner merges PR #1; Codex re-checks T-002 v1.1.

## Blockers

- IBKR account not yet approved → T-004 Table A blocked.
- None for Claude: GitHub is linked and Claude can push.

## Next

1. Owner: merge PR #1 (T-001), then the T-002 v1.1 PR once Codex accepts it.
2. Codex: re-check T-002 v1.1 against `docs/decisions/0002`. Independently reproduce at least S1 (STALE, GAP), O7, O9 and one V case. Mark Accepted or return findings.
3. When T-002 is Accepted and T-001 merged, T-003 becomes Ready for Codex.
4. Owner: decide the stop-date convention and budget when ready; neither blocks the work above.

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
