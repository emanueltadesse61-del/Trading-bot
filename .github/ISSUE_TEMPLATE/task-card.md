---
name: Task card
about: One focused unit of work for a single PR
title: "T-xxx: <short name>"
labels: ["state:draft"]
---

## T-xxx: <short name>

**State:** Draft | Ready | Implementing | Review | Changes requested | Accepted | Merged
**Phase:** <0–7>   **Author:** <Claude/Codex/owner>   **Implementer:** <Codex/Claude/owner>
**Depends on:** <T-xxx accepted / none>

### Goal
<One sentence.>

### Inputs
<Documents, files, data and interfaces this task relies on. Name sections.>

### Outputs
<Modules, functions with exact signatures, files, docs.>

### Evidence
<For any strategy or risk rule: the `docs/research/strategy_evidence.md` row it implements, or "hypothesis — no direct evidence". "Not applicable" for pure engineering.>

### Constraints
<Rules that must hold, e.g. "signal at t reads only rows dated <= t", "no network access".>

### Acceptance criteria
- [ ] <Specific, checkable criterion, with expected values where numeric>
- [ ] <Edge case>
- [ ] `docs/handoff.md` updated

### Exclusions
<What this task must not touch or add.>

### Open questions
<Must be empty before the card can be Ready.>
