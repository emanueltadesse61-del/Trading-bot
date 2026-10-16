# 0004 — Claude implements T-003 and drafts T-004 while Codex is offline

Date: 2026-10-16. Status: Accepted by the owner ("continue with all of the work as previously agreed and it will be reviewed once Codex is live").

## Context

`AGENTS.md` assigns implementation to Codex and review to Claude. Codex is temporarily unavailable. The owner asked Claude to continue the agreed work, with Codex reviewing when it returns.

## Decision

- For T-003 and T-004 only, the roles swap: **Claude implements, Codex reviews.** The rule that no model approves its own work still holds. Neither PR is merged until Codex has reviewed it and the owner approves.
- Claude follows every other rule in `AGENTS.md`: a separate branch, the PR template, no fixture edits, no broker access, no spending.

## The independence problem, and how it is contained

Claude wrote both the spec and the reference fixture, so a Claude implementation that passes the fixture is weaker evidence than a Codex implementation would have been.

- **Mitigation 1.** Codex has already independently reproduced W1, W2, W3, W4, W5, O1, O2, the full S1 signal case, O7, O9, V2, W8 and V9 from the spec (T-002 reviews at `c949dfd`, `c457ca5`, `4d4bc93`). Those fixture values therefore rest on two independent calculations.
- **Mitigation 2.** The implementation is written fresh from the spec, inside the repository's package structure. Claude's reference calculator stays outside the repo and is not copied.
- **Mitigation 3.** Codex's review of T-003 checks the code against the spec, not just the green tests. It looks for any behaviour the fixture doesn't pin down: untested branches, edge cases and tolerance handling.

## Tooling limitation

Claude's workspace cannot reach PyPI, so `uv`, `pytest` and `ruff` cannot run there. Claude runs the tests with system Python (numpy and pandas available) and a minimal pytest stand-in. **GitHub CI on the PR is the authoritative check.**

## Consequences

When Codex returns, its first tasks are reviewing the T-003 PR and the T-004 draft. Roles revert to `AGENTS.md` for T-005 onward unless the owner decides otherwise.
