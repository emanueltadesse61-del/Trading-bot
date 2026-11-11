# Trading bot

A deterministic trading research project in Phase 0: feasibility and synthetic verification before any broker integration. AI assists engineering and independent review; it does not produce trading signals. Real-money trading, funding and purchases are not authorised. The package contains the portfolio engine and local data tools; broker execution is not implemented.

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
T-007 adds canonical CSV import and verified raw Parquet storage. Real-feed integration remains future work.


## Importing real data (owner only)

These are instructions for the owner, **not permission to import real data now**.
The charter must confirm the holdout boundary before development data enters an
agent workspace. D5 must establish source adequacy. No funding, broker access,
downloads or purchases are performed by these tools. Development and CI use only
synthetic inputs.

Install the locked environment with `uv sync --locked` in a clean checkout of the
reviewed commit. The command records that checkout's Git HEAD as `code_commit`;
use a clean checkout so it accurately identifies the code. The owner keeps the
original full-history export outside the repo and **every** agent workspace.
Supply every workspace root; the guard cannot discover ones you omit. Run one
split at a time, without moving paths or changing symlinks while it runs.

The source directory requires four UTF-8 without BOM, comma-separated files:

| File | Header |
|---|---|
| `prices.csv` | `instrument,date,close,unit` |
| `distributions.csv` | `instrument,ex_date,amount,unit` |
| `calendar.csv` | `date` |
| `declarations.csv` | `instrument,price_semantics,distributions_complete,corporate_actions_none_through,evidence_source,checked_on` |

T-010 also supports CSV v2. Calendar and declaration headers are unchanged;
both market files must use matching versions:

| File | v2 header |
|---|---|
| `prices.csv` | `instrument,date,open,close,unit` |
| `distributions.csv` | `instrument,ex_date,pay_date,amount,unit` |

An empty `open` means unknown; supplied opens must be finite decimal numbers.
Every v2 distribution needs an ISO `pay_date` on or after its ex-date. Distribution
histories come from issuer sources with owner-recorded evidence; price bars alone
do not provide them. Pay dates after the holdout boundary may accompany earlier
ex-dates, subject to the point-in-time evidence requirement below.

The private parser returns `(ParsedImport, "v1" | "v2")`. `trader-split` carries
that header-derived version to both manifests, including header-only distributions
and all-empty opens. The public `import_csv` signature and `RawDataset` return
type are unchanged. `write_raw_dataset(..., schema="v1")` retains its default
and v1 bytes. Select `schema="v2"` explicitly for rich records; v1 refuses opens
and pay dates instead of dropping them. V2 refuses missing, wrongly typed or
pre-ex-date pay dates. The reader validates both schemas.

Dates use `YYYY-MM-DD`. Units are the feed's original labels (`GBP` or `GBX`),
never guessed. A header-only distributions file means confirmed no cash payments,
not a missing export. Each source instrument requires one evidence-backed
owner declaration: `unadjusted_close`, `true` for distribution completeness,
no unsupported corporate actions through at least its last market record, a
nonempty evidence source, and a check date no earlier than that coverage date.
An instrument with a split is unsupported. Jump checks do **not** prove that no
split happened. Declaration dates keep their true values, even after the holdout
boundary; they are source-quality attestations, never trading inputs.

First propose a boundary, without writing datasets (replace the example paths
with owner-controlled paths outside agent workspaces):

```sh
uv run trader-split --propose-holdout \
  --source /owner-private/export --repo-root /projects/Trading-bot \
  --agent-workspace /projects --agent-workspace /other-agent-workspace
```

This requires no output, boundary or provenance flags. It reports the four-year
proposal only if every instrument has 1,009 valid development closes and at least
one holdout close. Insufficiency reports do not silently shorten the holdout.
The owner records the chosen date in the charter before any performance is
computed. The weekday calendars in tests are synthetic, not an LSE calendar.

After those prerequisites are satisfied, the owner runs the split once with the
confirmed boundary and actual source/retrieval metadata:

```sh
uv run trader-split --source /owner-private/export \
  --holdout-start YYYY-MM-DD \
  --dev-out /projects/Trading-bot/data/development \
  --holdout-out /owner-private/locked-holdout \
  --repo-root /projects/Trading-bot \
  --agent-workspace /projects --agent-workspace /other-agent-workspace \
  --source-label SOURCE --adapter-version VERSION \
  --retrieved-at YYYY-MM-DDTHH:MM:SSZ
```

The command guards source files (including symlink targets), checks disjoint
paths, then validates both staged partitions. Each output contains four Parquet
files and `manifest.json`. Holdout publishes first and development last. Atomic
publication is **per dataset**, not a transaction across the pair. Caught errors
roll back outputs created by that invocation. An interruption can leave a
holdout output or staging folders; a retry refuses and names those leftovers
with `SPLIT_OUTPUT_EXISTS` or `SPLIT_STAGING_EXISTS`. The owner inspects the named
paths, removes only the outputs/staging folders belonging to the interrupted
attempt, and reruns. Do not delete the source export. The program never removes
pre-existing outputs for you.

Only development data may enter agent workspaces. The public Python `import_csv`
requires a boundary and refuses market events on or after it. Its synthetic mode
requires `SYN_` ids; that naming convention is a test guard, not proof that data
are synthetic or authorization to disguise real data.

`read_raw_dataset` verifies file hashes, schemas, summaries, declarations and the
partition boundary before returning records. Pin the printed `dataset_id` (files
plus partition and boundary), and `manifest_digest` when recording source/code
provenance. The digest is returned separately, not written into its own hashed
manifest. Integrity is relative to these pinned values; the files are not signed.
The builder still reports price-quality errors; storage validity does not prove
that prices are tradable or that a strategy works.

T-007 safety follow-ups: `trader-split` refuses tracked local edits with
`SPLIT_DIRTY_CHECKOUT` (including proposal mode). Commit or discard those edits
before importing so the recorded code version identifies the running checkout.
`SPLIT_PARTITION_MISMATCH` means verification found a missing, duplicated or
changed record across the two partitions; neither output is published.

## Synthetic backtest machinery

`trader.backtest` implements backtest spec v1.3. Construct `Market` with canonical
records and an exchange calendar, a generator with explicit instruments, and
`BacktestParams(HALF_SPREAD=...)`. Call `run_backtest` with date-valued `start`
and `end` and either `schedule="weekly"`/`"monthly"` or explicit `decision_dates`.
Results contain the daily ledger, decisions, descriptive metrics, anomaly totals
and input provenance. Strategy generation reuses the accepted portfolio engine.
Only synthetic use is supported at this stage. Gate 3 statistics and the
real-data activation evidence remain prerequisites.

`market_from_raw(dataset_dir, exceptions, exceptions_version)` reads and validates
the directory itself and returns `(Market, manifest)`. Only raw schema v2 is
accepted; v1 gives `BACKTEST_RAW_SCHEMA`. The bridge preserves the records and
parsed approval snapshot. No caller-supplied schema label is accepted. Simulator
admission still checks market quality; storage integrity is not trading validity.

Dividend cash settles at the first supplied session **after the ex-date** and
**on or after the pay date**. Weekend dates move to the next session, and same-day
payments wait until the next session. Cash due beyond the run remains unsettled
in NAV. Synthetic distributions without pay dates retain `DISTRIBUTION_LAG`.
Invalid types or pre-ex-date pay dates give `BACKTEST_PAY_DATE` for in-scope records.

This is a **declared model**, not evidence that a broker credits cash before the
pay-date open. Before real activation, backtest spec §12 requires cash-timing
evidence or an owner-approved convention plus a later-credit sensitivity run,
and evidence that pay dates were announced by ex-date (or a gate excluding
retrospective revisions). Gate 3 statistics and a frozen, registered hypothesis
are also required. None of that evidence is supplied by this build.

Supply the frozen jump-approval snapshot and version on `Market`. The strategy
generator defaults both optional approval arguments to `None`, so it uses that
market snapshot unchanged. If supplied, generator approval arguments are assertions
that must match the market snapshot/version; conflicts raise `BACKTEST_PARAMS`.
`rebalance` trades only target keys: an omitted held instrument is retained; an
explicit zero target requests an exit. Baselines report `BLOCKED_NAV` for NAV ≤ 0.

## Running backtests through the registry

`trader.registry` implements registry spec v1.2.1. `run_synthetic` accepts an
immutable `RunDescriptor`, a synthetic `Market`, an ISO-string `period` object,
a cost multiplier and a note. All instrument ids must start with `SYN_`; this
convention is a test guard, not permission to relabel real data. The descriptor
contains the complete configuration defined in registry spec §2. Its values
construct the accepted generator and simulator parameters; opaque or scripted
generators cannot supply registry provenance. The returned `RecordedRun` holds
the backtest result, run id, durable trial count and checkpoint used.

Create a disposable registry **outside the repository** for synthetic work:

```bash
uv run trader-registry init /tmp/trader-synthetic-registry.sqlite
uv run trader-registry verify /tmp/trader-synthetic-registry.sqlite
uv run trader-registry checkpoint /tmp/trader-synthetic-registry.sqlite
```

Initialization refuses an existing file. Each command prints JSON. For a manual
checkpoint comparison, save the printed head outside the repository, then use
`verify PATH --checkpoint FILE` or `summary PATH --checkpoint FILE`. Summary
includes completed, failed, unfinished and superseded runs. These commands do
not create or commit `research/registry-checkpoint.json`.

Each run start commits **before** simulation; its finish commits separately.
An ordinary failure is recorded and re-raised. Process death leaves a visible
unfinished run. A rerun may name an earlier run with the same hypothesis,
configuration and kind in `supersedes`; it never erases that earlier run.

`parse_preregistration` checks the strict JSON block, every resolved variant,
and costs at every declared multiplier. `register_hypothesis` requires a clean
checkout, a committed, complete frozen hypothesis and a committed checkpoint.
The registry treats untracked, non-ignored files as dirty, as well as tracked
edits. Ignored files do not mark it dirty. Keep temporary files outside the
checkout or in an appropriate ignored location; never commit data or secrets to
satisfy the guard. Synthetic runs may be dirty and record that fact.
Registration permanently consumes its strategy-variant count from the 20-trial
budget, even if the file is later deleted or demoted. Baselines and synthetic
runs do not consume trials. H-001 remains draft and unregistered in this build.

Write operations read their checkpoint from **committed HEAD**, never a caller's
file or working-tree edit. The clock (zero-argument ISO UTC string function), Git
access (`root`, `commit()`, `clean()`, `committed(relative_path)`), checkpoint
provider (`provider(git)`) and hypothesis resolver (`resolver(parsed_contract)`)
are injectable for synthetic tests. The production defaults use the checkout's
Git objects. `run_registered` accepts neither a custom configuration nor period;
it checks registration, file and config hashes, declared costs, dataset identity,
development partition and approval snapshot. **Real execution is disabled**:
`SUPPORTED_REAL_SCHEMAS` is empty, so even a fully matching request ends with
`REGISTRY_REAL_DATA_UNSUPPORTED`, without a start row or simulator call.
The set is the actual capability check. Its unreachable supported branch raises
`NotImplementedError` until the Gate 3 activation card implements registered
execution. CLI failures without a more specific named code use `REGISTRY_CLI_ERROR`.

Before future real use, the owner initializes the permanent external registry
and commits its initial checkpoint through review. The policy then requires a
new committed checkpoint after **every registration and every real-run session**;
a Gate 3 report must cite a checkpoint covering every run it uses. The registry
id cannot be reset without an explicit owner decision. Hash verification detects
edits and middle deletions. A checkpoint also detects truncation up to its saved
head and replacement of the registry. Deletion **after** that checkpoint remains
undetectable; verification without one proves only internal consistency. This
is tamper evidence relative to a trusted checkpoint, not authenticity or a backup.
