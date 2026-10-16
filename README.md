# Trading bot

A deterministic trading research project in Phase 0: feasibility and synthetic verification before any broker integration. AI assists engineering and independent review; it does not produce trading signals. Real-money trading, funding and purchases are not authorised. The current package is an empty skeleton, not a trading system.

## Development

Install Python 3.12 and uv, then run from the repository root:

```sh
uv sync --locked
uv run ruff check .
uv run pytest -q
```

Read [the current handoff](docs/handoff.md) first, then [agent working rules](AGENTS.md) and the assigned task card. Claude and Codex use separate checkouts; the owner approves merges.

The import guard detects direct Python imports of forbidden SDKs under `src/`. It is a regression check, not a sandbox or a guarantee against dynamic imports or network access. Broker credentials and holdout data must remain outside agent and CI environments.


The data component now builds engine inputs from canonical synthetic price and
cash-distribution records (data spec v1.1), with explicit feed units, session gaps,
quality reports and exception-snapshot digests. Its holdout-path guard checks
repository and supplied workspace containment; it does not authorise data access.
Storage and real-feed integration remain future work.
