# Architecture

Status: **Proposed — v1.** Last updated: 2026-10-16.

## 1. Principles

1. **Deterministic trading path.** Data → checks → signals → portfolio → risk gate → order manager → broker. Same inputs, same outputs. **No LLM call anywhere in this path**, and the live system keeps working safely if every AI provider is unavailable.
2. **One Python application, one process per job.** No microservices, queues, dashboards or databases beyond SQLite in v1.
3. **Shared logic, separate execution.** Backtest and paper/live trading import the same `signals` and `portfolio` code. Fills, cash settlement and account state still differ between simulation and broker; the backtest is not "exactly what trades".
4. **Permission boundaries are enforced, not requested.** Agents work in research checkouts with no broker credentials, no network path to the broker, and no holdout data.
5. **Fail closed.** Any unknown state blocks new orders and alerts the owner. Nothing sells automatically because of bad data.

## 2. Components

```text
src/trader/
  data/        download, validate, store (Parquet + manifest per dataset)
  signals/     pure functions: price history up to t -> trend score, momentum return, sigma, covariance
  portfolio/   pure functions: signals -> target weights (docs/portfolio-spec.md §5)
  planner/     pure function: targets + holdings + cash -> orders or BLOCKED (spec §6)
  risk/        pre-trade gate; imports nothing from signals/portfolio
  backtest/    daily simulator, cost model, baselines, metrics
  execution/   broker adapter (IBKR via ib_async, paper first), order manager, reconciliation
  monitor/     daily checks, alerts, external heartbeat pings, kill switch
  registry/    experiment registry (SQLite)
```

| Boundary | Inputs | Outputs | Must not |
|---|---|---|---|
| data | Vendor/broker files | Validated Parquet + manifest (source, range, SHA-256) | Silently fill gaps |
| signals | `tr_close` up to t | s, M, σ, Σ, eligibility | Read any row dated after t |
| portfolio | Signals, classes | Weights + diagnostics | Know about holdings or cash |
| planner | Weights, holdings, prices, cash, preconditions | Orders or a BLOCKED code | Use unsettled cash; sell for data reasons |
| risk | Proposed orders, account state | Approve / reject per order | Be bypassed; depend on strategy code |
| execution | Approved orders | Broker orders, fills, state records | Retry blindly after a timeout |
| monitor | Ledger, account, heartbeats | Alerts, pause/cancel | Liquidate without owner sign-off |

The exact portfolio algorithm is in **`docs/portfolio-spec.md`**; this document does not restate it, to keep one source of truth. Summary: equal capital to a trend sleeve and a momentum sleeve (top 4 with positive 12-1 return), inverse-volatility weights within each, 25% asset cap, 60% class cap with proportional reduction, a 10% portfolio-volatility ceiling that only scales down, remainder in GBP broker cash, 2-point actual-vs-target rebalance bands, settled-cash buys, and a post-trade constraint check with one repair pass.

## 3. Schedules

| Job | When | Does |
|---|---|---|
| Weekly plan | Fixed weekday after the close (exact time fixed in Phase 0) | Signals, targets, order plan |
| Order watch | During each trading run | Tracks every order to filled, cancelled or rejected |
| Daily check | Every trading day | Reconciliation, drawdown, data freshness |
| Heartbeat | Every job | Pings an external uptime monitor; a missing ping alerts the owner, catching a run that never started |

## 4. Failure behaviour

| Event | Response |
|---|---|
| Data check fails | `BLOCKED_DATA`; no orders; alert |
| Reconciliation mismatch | `BLOCKED_RECONCILIATION`; no orders; alert |
| Order state unknown (timeout, outage) | Record `UNKNOWN` durably; block new orders; alert; query broker and reconcile before resuming. Never resubmit blindly |
| Order rejected | Record; alert; no automatic retry in the same run |
| Partial fill | Recorded; exposure counts filled quantity plus open remainder |
| Constraints still violated after repair | `BLOCKED_CONSTRAINTS`; alert |
| Drawdown 15% from peak (paper) | Pause new orders; review |
| Drawdown 25% from peak (paper) | Stop the experiment; review |
| Missed heartbeat | External alert; next run starts with reconciliation |

Kill-switch levels are distinct: **Pause** (no new orders), **Cancel** (cancel open orders), **Flatten** (sell all into broker cash, manual sign-off only).

## 5. Environments and permissions

| Environment | Who | Broker credentials | Holdout data | Can submit orders |
|---|---|---|---|---|
| Agent checkouts (Claude, Codex) | Models | None | None | No |
| CI | GitHub Actions | None | None | No |
| Owner research machine | Owner | None | Yes, for the one-time evaluation | No |
| Paper runtime | Scheduled jobs | Paper only | None | Paper account only |
| Live runtime | Not authorised | — | — | — |

Configuration lives in `config/paper/` (changes via normal PR review) and `config/live/` (does not exist until a live charter amendment). The environment is chosen explicitly at start-up; there is no default.

## 6. Storage

- Market data: Parquet, outside Git, with a manifest committed per dataset.
- Ledger (orders, fills, positions, decisions): SQLite, outside Git, backed up.
- Experiment registry: SQLite, append-only; every backtest run writes a row automatically.
- Every decision record carries the code commit and config hash.

## 7. Stack

Python 3.12, pandas, NumPy, pytest, a lockfile-based dependency manager (chosen in T-001), Parquet, DuckDB for ad-hoc research, SQLite, `ib_async` for IBKR (Phase 4, not before Gate 3), cron or an equivalent scheduler, email or Telegram alerts.

Deferred: React dashboard, PostgreSQL, ML models, LLMs in the loop, streaming data, microservices, Docker for deployment until a host is chosen.
