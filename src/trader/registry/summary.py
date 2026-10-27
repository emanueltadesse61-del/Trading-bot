"""Summaries derive counts from permanent events, never hypothesis files."""

import sqlite3

from .errors import RegistryError
from .store import head, location, read_rows, verify_rows


def summarize(rows, checkpoint=None):
    events = verify_rows(rows, checkpoint)
    registered = [e for e in events if e["type"] == "hypothesis_registered"]
    starts = {e["run_id"]: e for e in events if e["type"] == "run_started"}
    ends = {e["run_id"]: e["outcome"] for e in events if e["type"] == "run_finished"}
    counts = {}
    for run, e in starts.items():
        key = f"{e['hypothesis_id']}/{e['variant_id']}"
        group = counts.setdefault(key, {"completed": 0, "failed": 0, "unfinished": 0})
        group[ends.get(run, "unfinished")] += 1
    return {
        **head(rows),
        "checkpoint_used": checkpoint,
        "trial_count": sum(len(e["variants"]) for e in registered),
        "registered_hypotheses": registered,
        "runs_per_variant": counts,
        "runs": {str(run): ends.get(run, "unfinished") for run in starts},
        "superseded": sorted(
            {e["supersedes"] for e in starts.values() if e["supersedes"] is not None}
        ),
    }


def registry_summary(path, checkpoint=None):
    path = location(path)
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            return summarize(read_rows(db), checkpoint)
    except sqlite3.Error as exc:
        raise RegistryError("REGISTRY_CHAIN_BROKEN", str(exc)) from exc
