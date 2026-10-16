# Working Rules for AI Agents

These rules apply to Codex and Claude alike. `CLAUDE.md` points here so both models read the same text.

## Start of every session

1. Read `docs/handoff.md`. It is the current state of the project.
2. Read the task card you are working on (`docs/tasks/T-xxx.md` or its GitHub issue) and every document it lists under Inputs.
3. If the handoff, the card and the code disagree, stop and report the contradiction. Do not pick one silently.

## Roles

| Role | Responsibilities | Never |
|---|---|---|
| Owner (Samuel) | Scope, spending, capital, merges, releases, gate decisions; relays handoffs between models | — |
| Claude | Architecture, research protocol, task cards, independently calculated reference cases, code review | Approve its own specs as final; implement code it will also review |
| Codex | Checks task cards before building, implements, tests, debugs, prepares PRs | Approve its own PRs; change a spec to make code pass |
| Deterministic software | Signals, limits, order tracking, reconciliation, records | Call an LLM |

Neither model approves its own work. Neither model merges, deploys, spends money, places orders, or handles secrets.

## The seven-step loop

1. **Claude writes one task card** (template: `.github/ISSUE_TEMPLATE/task-card.md`).
2. **Codex checks the card before building.** Material ambiguities go back to Claude through the owner; routine implementation choices stay with Codex.
3. **Codex implements in its own checkout** on a branch named `t-xxx-short-name` and opens a focused PR using `.github/pull_request_template.md`.
4. **CI runs.** Red means back to Codex.
5. **Claude reviews that exact commit.** Each finding names the requirement it breaks or a concrete failure scenario.
6. **Codex fixes findings**; material changes get another review.
7. **The owner merges.** A passed review never authorises funding or deployment.

Task states: `Draft → Ready → Implementing → Review → Changes requested / Accepted → Merged`. A card is **Ready** only when someone other than its author could judge whether it is done.

## Hard rules

- **Separate checkouts.** Each model works in its own clone or worktree. Never edit the same checkout concurrently.
- **No secrets.** No credentials, API keys or account numbers in the repo, in prompts or in logs. `.env` files are gitignored.
- **No broker access from agent environments.** No network calls to the broker; no orders, paper or live.
- **No holdout access.** Holdout data never exists in an agent workspace.
- **No spending.** Never sign up for or purchase a data feed, hosting or tool. Propose it to the owner with the cost.
- **No changes to `config/live/`.** It does not exist until a live charter amendment.
- **Specs win over code.** If code and `docs/portfolio-spec.md` disagree, the code is wrong unless a decision record amends the spec.
- **Fixtures are not edited to make tests pass.** A fixture mismatch is a disagreement (below).
- **Every backtest run is registered.** Never run a strategy evaluation outside the registry.
- **Strategy changes are experiments, not edits.** A proposed change to a rule or parameter (a lookback, a cap, a threshold) is pre-registered and evaluated under `docs/research-protocol.md`. It is never applied directly to the spec, `Params` or `config/` because it improved a backtest. `tests/unit/test_params_frozen.py` fails if a parameter changes without its approved value being updated alongside a decision record.
- **Claims need evidence.** A rule presented as established must cite `docs/research/strategy_evidence.md`; otherwise it is labelled a hypothesis.
- **No LLM in `src/`.**

## Evidence-based handoffs

A handoff states what was done, at which commit, with which commands and results. "Done" without evidence is not a handoff. At the end of every session, update `docs/handoff.md`:

- Move finished items to Completed, with the commit hash.
- Separate **planned** checks from **completed** checks, and paste the actual command output summary for completed ones.
- List blockers and the next task.

## Disagreements

1. State both readings precisely.
2. Identify the calculation, test, source or failure scenario that separates them.
3. Run the smallest check that decides it.
4. Record the outcome in `docs/decisions/NNNN-title.md`.

The owner decides scope and financial risk. Technical questions are settled by evidence, not by which model sounds more convincing.

## Scope guard

Out of scope until a charter amendment: futures, shorting, leverage, options, ML models, dashboards, autonomous strategy promotion, a second broker, live trading.
