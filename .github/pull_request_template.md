## Handoff

**Card:** T-xxx   **Branch:** `t-xxx-short-name`   **Commit for review:** `<full SHA>`

### What changed
<Files and why, in a few lines.>

### Tests
| Command | Result |
|---|---|
| `<exact command>` | <pass/fail summary, counts> |

Checks **planned but not run**, if any: <list or "none">

### Evidence
<Strategy or risk changes only: the evidence-map row or decision-log entry this relies on, or "none".>

### Assumptions
<Anything the card did not specify, and the choice made.>

### Data used
<Dataset IDs and manifest hashes, or "synthetic only". Never the holdout.>

### Experiments
<Registry IDs created, including failures, or "none".>

### Unresolved issues
<Known gaps, follow-ups, or "none".>

### Checklist
- [ ] Matches the task card's acceptance criteria
- [ ] No secrets, broker calls, spending or `config/live/` changes
- [ ] Fixtures unchanged, or the change is backed by a decision record
- [ ] Strategy parameters unchanged, or the change is a registered experiment with a decision record
- [ ] `docs/handoff.md` updated
