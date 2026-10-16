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

The source directory requires four UTF-8, comma-separated files:

| File | Header |
|---|---|
| `prices.csv` | `instrument,date,close,unit` |
| `distributions.csv` | `instrument,ex_date,amount,unit` |
| `calendar.csv` | `date` |
| `declarations.csv` | `instrument,price_semantics,distributions_complete,corporate_actions_none_through,evidence_source,checked_on` |

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
