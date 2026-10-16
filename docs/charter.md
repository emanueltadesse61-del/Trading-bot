# Project Charter

Status: **Phase 0 — feasibility.** Last updated: 2026-10-16. Owner: Samuel (product owner and release authority).

Each entry is marked **Confirmed** (decided by the owner), **Proposed** (a default in force until the owner changes it) or **Open** (unresolved; must not be assumed).

## 1. Objective

Build a deterministic, systematically tested trading system and find out, with evidence, whether a diversified trend-and-momentum ETF portfolio improves a declared risk objective against a passive benchmark after costs. "No edge found" is a valid, useful outcome.

## 2. Authorisation

| Item | Status | Entry |
|---|---|---|
| Current scope | Confirmed | Phase 0 feasibility, then gated development and paper trading |
| Real-money trading | Confirmed | **Not authorised. £0 real capital.** No account funding |
| Spending | Confirmed | **No purchases authorised.** Any subscription or hosting spend needs the owner's explicit approval first |
| Live capital, live loss limits | Open | Decided separately, by a charter amendment, only after Gate 5 |

### Paper experimentation vs live authorisation

Paper trading and live trading are separate authorisations. Passing every paper gate does **not** authorise real money. A live release requires a new, signed charter section stating capital, monetary loss thresholds, account type and the release commit. Nothing in this repository may treat the paper configuration as permission for live trading.

## 3. Account and jurisdiction

| Item | Status | Entry |
|---|---|---|
| Residence | Confirmed | United Kingdom |
| Broker | Proposed | Interactive Brokers (IBKR); new account being created by the owner |
| Account type | Proposed | Cash account (no margin), ETF trading permissions only |
| ISA wrapper | Open | Deferred until real capital is considered |
| API access, permissions, market-data entitlements | Open | Verified in T-004 once the account exists |

Account approval must not block specifications, repository setup or synthetic tests.

## 4. Paper experiment parameters

| Item | Status | Entry |
|---|---|---|
| Simulated starting balance | Proposed | £10,000 (an engineering test case, not an investment recommendation) |
| Pause threshold | Proposed | Equity 15% below its running peak → pause new orders and review |
| Stop threshold | Proposed | Equity 25% below its running peak → stop the paper experiment and review |
| Example | — | From a £10,000 peak: pause at £8,500, stop at £7,500. Thresholds move up with new peaks |
| Nature of thresholds | Confirmed | Intervention points, not guarantees. Gaps, halts and outages can carry losses past them |
| Reset rule | Confirmed | A stopped experiment stays recorded. The paper balance is never reset to erase losses |

## 5. Budget and time

| Item | Status | Entry |
|---|---|---|
| Data and hosting ceiling | Proposed | £600 a year (£50/month), excluding existing AI subscriptions. Not a spending approval |
| Default | Proposed | Work locally; spend only where a feasibility check shows a need, with owner approval |
| Time commitment | Confirmed | Flexible, in bounded weekly milestones |
| Research stop rule | Open | Week-20 decision point is proposed; whether it counts calendar weeks or worked weeks is undecided (see `docs/handoff.md`) |

## 6. Research constraints

| Item | Status | Entry |
|---|---|---|
| Market | Proposed | About 12 liquid UCITS ETFs, finalised by the T-004 instrument matrix |
| Rebalancing | Proposed | Weekly; decision time, execution session and holiday rules fixed in Phase 0 |
| Deciding benchmark | Proposed | 60/40 equity/gilt portfolio, monthly rebalanced, same cost conventions |
| Other comparisons | Proposed | Global equity buy-and-hold; 10-month moving-average rule |
| Primary objective | Proposed | Gate 3 rule in `docs/research-protocol.md`, after costs and before personal tax |
| Trial budget | Proposed | At most 20 registered strategy variants, robustness variants included |
| Holdout | Proposed | Most recent **4 years** of usable history. The exact start date is fixed mechanically from history availability (T-007) and written here **before any performance is computed**; it is never chosen to include or exclude a particular market event. Evaluated once, by the owner |

### Permanent rules

1. **Trial history is never reset.** Every registered variant, including failures and abandoned runs, stays in the experiment registry and counts against the budget. A new charter inherits the count.
2. **An inspected holdout is consumed.** Once any result on the holdout has been seen, that period is never treated as unseen again, under any charter, strategy name or fallback.
3. **A fallback strategy earns its own approval.** A simpler strategy (for example the moving-average rule) adopted after a holdout has been inspected does not inherit that holdout's pass; it needs fresh evidence (new paper period).
4. **No LLM output is a trading signal.**

## 7. Out of scope for this charter

Futures, short selling, leverage, options, machine learning models, dashboards, autonomous strategy promotion, and any second broker.

## 8. Decision authority

| Decision | Who |
|---|---|
| Scope, spending, capital, loss thresholds | Owner |
| Merges and releases | Owner |
| Gate pass/fail | Owner, on evidence prepared by Claude and Codex |
| Technical disputes | Settled by tests, calculations or primary sources (see `AGENTS.md`) |
