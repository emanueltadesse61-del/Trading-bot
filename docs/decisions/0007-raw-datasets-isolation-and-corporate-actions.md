# 0007 — T-007 requirements: raw datasets, owner-run isolation, corporate actions

Date: 2026-10-16. Status: Proposed by Claude; pending Codex re-check and owner merge.
Review: Codex on PR #10 at `9b534c9` (record `33ace48`, now merged into the branch).
Changes: `docs/data-spec.md` v1.2 (§8.1, §8.3–8.5, §10); `docs/tasks/T-007-storage-and-import.md` v2.

## Codex's two answers — adopted

1. **`dataset_id`** is a content identity: SHA-256 of canonical JSON with a schema version and a filename-keyed map of file digests. Provenance (retrieval time, source label, code commit) is kept out of the identity. Byte identity is promised only under the pinned writer settings and library version.
2. **One owner-facing command** (`trader-split`), built from internals that can each be tested on their own. No intermediate full-history dataset is written.

## B1 — Contradictory import contract; source not guarded — **Accepted**

**Decision.**
- **Two paths.** The public `import_csv` keeps refusing a missing holdout start (`IMPORT_HOLDOUT_REQUIRED`). Only `trader-split` uses the private full-history parser.
- **Preflight before any read:**
  - guard the source directory, each resolved input file and the holdout output;
  - require source, development and holdout locations to be disjoint by text and by filesystem identity;
  - refuse outputs that already exist;
  - require at least one agent workspace.
- **Staged, verified, atomic publish.** A failed run leaves nothing usable behind.
- **Tests:** a forbidden source, a symlinked input into a workspace, overlapping outputs, and an unreadable source.

## B2 — Storage contract didn't match the spec — **Accepted**

**Decision.** T-007 stores **raw imports only**.
- Spec §8.1 now separates the raw-dataset manifest from build provenance.
- Exceptions provenance belongs to each build, recorded in the run registry from T-008, so it is not invented for raw data.
- `RawDataset` carries `partition` and `holdout_start`, so manifests have a real source for them.

Spec §8.4 defines:
- the exact five-file layout (manifest inside the directory);
- the content identity;
- the manifest fields;
- **full validation on read**: schema; exact file set; hashes and row counts; recomputed `dataset_id`; `date_range` and instrument summaries re-derived from the data; partition rules applied to every dated row.

Empty partitions are refused at split time. The integrity-versus-authenticity limitation is stated: runs pin `dataset_id`.

## B3 — False split-detection claim — **Accepted (my error)**

**Issue.** I claimed a split of 1.33:1 or more would be caught by the >25% jump check. Exact arithmetic:

| Split | Price drop | Flagged? |
|---|---|---|
| 4:3 | exactly 25% | No |
| 1.33:1 | 24.81% | No |
| 1.2:1 | 16.67% | No |

Ordinary market moves can also mask larger splits.

**Decision.** The jump check is stated to be an anomaly check, not split detection. Real use requires an owner **declaration per instrument** (spec §8.5): unadjusted-close semantics; distributions complete; no non-cash corporate action up to a date covering the instrument's last record; an evidence source; a check date. An instrument that did have a split cannot be declared and is unusable until split support is specified. Approving a split-induced jump as cleaning stays prohibited.

## Clarifications — adopted

- **Holdout proposal rule** (T-007 Output 5). The end session E is the last session imported. H is the first session on or after E minus 4 calendar years (29 Feb becomes 28 Feb). Every instrument needs ≥ 1,009 development closes before H (253 warm-up + 756) and at least one close on or after H. Insufficiency produces a report and no date; it is the owner's decision, never a silent shortening. The owner confirms H in the charter before any performance is computed.
- **Distribution completeness.** `distributions.csv` is now required, with header-only allowed, and the declaration must assert completeness. A missing export is never read as "no payments".
- **Error codes named:** `IMPORT_HOLDOUT_REQUIRED`, `IMPORT_MISSING_FILE`, `IMPORT_BAD_HEADER`, `IMPORT_MALFORMED_ROW`, `SPLIT_PATHS_OVERLAP`, `SPLIT_OUTPUT_EXISTS`, `SPLIT_EMPTY_PARTITION`.
- **Stale text removed:** "account approval pending" is gone from the card. IBKR approval (2026-10-16) does not establish that the data is adequate (D5).

## Consequences

T-007 returns to requirements review. Data spec §1–7, §9 and the fixture are unchanged, so T-006 is unaffected.

---

## Re-review of v2 (Codex at `eb113a7`, record `de9bc49`): B1–B3 accepted; B4 and B5 raised

Data spec v1.2.1 and T-007 card v3.

### B4 — Copied declarations break the partition rules — **Accepted**

**Issue.** A full-source declaration has `corporate_actions_none_through` and often `checked_on` on or after H. Copied into the development partition, it failed the "every dated row before H" rule.

**Decision.**
- The partition rules apply to **market events** only: price `date`, distribution `ex_date`, calendar `date`.
- Declaration dates are **attestation dates**: later source-quality statements, never market information at a historical t.
  - They keep their real values, never backdated.
  - They are exempt from the partition rules.
  - They are never passed to `build_dataset`.
  - New rule: `checked_on` ≥ `corporate_actions_none_through`.
- Declarations are copied unchanged into both partitions and are excluded from the no-duplication assertion.
- Tests: a round trip with after-H attestation dates and pre-H prices; a market event on H is still rejected.

### B5 — Two renames are not one atomic publication — **Accepted (Codex's first option)**

**Issue.** An interruption between the holdout rename and the development rename leaves the holdout output alone. My "a failed run leaves nothing usable" overstated the algorithm.

**Decision.**
- Atomic publication **per dataset**, holdout first, **development last**.
- A caught failure rolls back everything.
- An interruption may leave an isolated holdout output. That is not a leak, and it never leaves a development dataset without its holdout.
- A re-run refuses while outputs or `*.staging-*` directories remain (`SPLIT_OUTPUT_EXISTS`, `SPLIT_STAGING_EXISTS`), naming them. The owner removes them and re-runs; the README documents this.
- No transaction system.
- Acceptance includes an `os._exit` interruption case and the retry.

### Clarifications — adopted

1. **Valid closes** are distinct calendar sessions with exactly one price record, a finite positive close and a supported unit. An instrument excluded under data spec §3 (evaluated at t = E) is insufficient, with its codes. The calendar is validated before E and H are derived.
2. **Proposal acceptance cases**, computed independently with weekday calendars:

   | Calendar | E | H | Development / holdout sessions | Result |
   |---|---|---|---|---|
   | 2018-01-01 to 2025-12-31 | 2025-12-31 | 2021-12-31 | 1,044 / 1,044 | Sufficient |
   | From 2019-01-01 | 2025-12-31 | 2021-12-31 | 783 development | Insufficient |
   | Ending 2028-02-29 | 2028-02-29 | 2024-02-28 | — | Leap-day mapping |

3. **§7.1:** the obsolete "dataset manifest records exceptions provenance" sentence now points to the run registry.
4. **Identity covers the boundary.** `dataset_id` now includes `partition` and `holdout_start`, so pinning it pins the boundary as well as the four files. Runs that need provenance pinned also record `manifest_digest`. This extends Codex's answer 1: provenance stays outside the identity, but these two fields define permitted use, so they are content.
5. **Proposal mode** lists its flags: source, repo root and workspaces only; no H, outputs or provenance.
