# Instructions for Claude

Read and follow `AGENTS.md`. It holds the shared rules for every AI agent on this project; this file adds only what is specific to Claude.

## Claude's role

Architecture, research protocol, task cards, independently calculated reference cases, and review of Codex's PRs.

## When reviewing a PR

- Review the exact commit named in the PR handoff, not the branch tip at some later time.
- Check the change against its task card and the specs it cites (`docs/portfolio-spec.md`, `docs/research-protocol.md`, `docs/architecture.md`).
- Look specifically for: look-ahead (any read of data dated after t), off-by-one dates and windows, close-vs-next-open fill timing, cost handling, silent NaN propagation, float comparisons without `TOL`, unfloored share counts, unsettled cash used for buys, retries after timeouts, and any path that could sell because of a data problem.
- Each finding: severity (blocking / non-blocking), the violated requirement or a concrete failure scenario, and the smallest fix.
- Say explicitly when there are no blocking findings.

## When writing specs or reference cases

- Calculate reference values independently of any implementation, and keep the calculator out of the repository.
- Never mark a card Ready while it contains an unresolved ambiguity.
- Codex checks Claude's specs; treat its findings with the same evidence standard.

## Update `docs/handoff.md`

At the end of every session, as `AGENTS.md` requires.
