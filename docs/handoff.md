# Handoff — read this first

Last updated: 2026-10-16 by Claude. Update this file at the end of every session (`AGENTS.md`).

## Current phase

**Phase 0 — feasibility.** No real money, no account funding, no purchases authorised (`docs/charter.md` §2).

## Review target

| Item | Value |
|---|---|
| Branch | `main` |
| Commit for review | `c949dfd5a9bdd16007025206415d51101406a2a3` |
| Under review | T-002 spec and reference cases (reviewer: Codex) |

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
| T-001 Repository bootstrap | **Ready** | Codex implements |
| T-002 Portfolio spec + reference cases | **Review** | Codex reviews, then marks Accepted or returns findings |
| T-003 Synthetic portfolio implementation | Draft (Ready when T-002 Accepted and T-001 merged) | — |
| T-004 Feasibility matrix | Ready (document); account rows **Blocked** | Codex drafts; owner does account checks |

Cards: `docs/tasks/`. Copy each into a GitHub issue when convenient; the files remain the reference until then.

## Completed

| Item | Commit | Evidence |
|---|---|---|
| Bootstrap documents, templates, task cards | `c949dfd` | Files listed below |
| T-002 deliverables (Claude) | `c949dfd` | Reference values computed by Claude's own calculator, kept outside the repo |

Bootstrap files: `AGENTS.md`, `CLAUDE.md`, `docs/charter.md`, `docs/architecture.md`, `docs/research-protocol.md`, `docs/portfolio-spec.md`, `docs/portfolio-reference-cases.md`, `docs/decisions/0001-record-decisions.md`, `docs/tasks/T-001…T-004`, `.github/ISSUE_TEMPLATE/task-card.md`, `.github/pull_request_template.md`, `tests/fixtures/portfolio_cases.json`.

## Checks

**Completed**
- Fixture loads and contains 10 cases: `python3 -c "import json; d=json.load(open('tests/fixtures/portfolio_cases.json')); print(len(d['weights'])+len(d['orders'])+len(d['signals']))"` → `10`.
- W1 and O1 hand-checked against the calculator (working in `docs/portfolio-reference-cases.md`).

**Planned (not yet run)**
- Codex's independent reproduction of W1, W4, O1, O2 (T-002 review).
- `uv sync --locked && uv run ruff check . && uv run pytest -q` and CI (T-001).

## Blockers

- IBKR account not yet approved → T-004 Table A blocked.
- None for Claude: GitHub is linked and Claude can push.

## Next

1. Owner: give Codex the handoff message (bootstrap is on `main`).
2. Codex: review T-002 (check only, no implementation), then implement T-001 on branch `t-001-bootstrap`.
3. Claude: review the T-001 PR and respond to T-002 findings.
