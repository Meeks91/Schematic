# Phase 8 field notes — creators-api (trengine), 2026-09-11

Observed while orchestrating 23 tasks on auto: Fable orchestrator, Opus driver per task group
(2–3 in parallel), Sonnet reviewer per task. Only items I am confident would help.

## 1. One source for the test list

`tasks.md` and the component card both carry test files/names; they drifted (e.4: the CLI
confirmation-gate test was in `tasks.md` and absent from `creatorRegistry_cli.md`). Phase 7
should reference the card's test table by name only and never restate it; `schematic validate`
can flag a `tasks.md` test file that no card lists.

## 2. Card templates must not encode names the standards ban

Two review rounds (e.2, c.6) were spent on the same finding: card test names carried a
`<method>_` prefix that `writing-tests §7` bans once the test class scopes the method. The
Phase 4 contract audit should check test names against the resolved testing module's naming
rule, so the card is right at lock and the reviewer never sees it.

## 3. `status` counts `review` as pending

`schematic status` folds tasks in `review` into the pending count; a task in its final review
looks not-started. Print `review` as its own line beside `in_progress` / `pendingInput`.

## 4. A design gap found before its task is claimable has no home

`task ask` requires a claimed task. The profile-pictures bucket-binding question surfaced while
e.2 was still blocked by a.2/e.1, so it went to the user in chat and was ledgered by hand.
Allow `task ask <tag>` on a pending task (question attaches; the task cannot be claimed until
answered), or add `schematic ask <schematic> "<question>"` for bundle-level gaps.

## 5. Parallel drivers need a file-ownership fact

Nothing in the CLI knows which files a claimed task owns, so concurrent drivers collided only
by luck (three transient full-suite failures during an in-flight rename). `task next` already
prints the card's Scope; record it on claim and let `task next` refuse a task whose Scope
overlaps an `in_progress` task's — or at least print the overlap so the orchestrator sequences
it.

## 6. `review sweep` needs a whole-diff mode — RESOLVED (2026-09-11)

Resolved by splitting the concern into two commands instead of one mode flag:
`review sweep` stays sharded (≤5 files) and STANDARDS-focused — it is the per-group
standards gate (#2), run at each task-group boundary, where the skip scopes it to the
group. Duplication/consistency moved to a new single-agent whole-diff command,
`review consistency` (#3), which reads the entire diff in one view (one pass, no loop)
and also runs the mechanical per-file line-limit check. Entry-point tracing is `review
e2e` (#4), gated on a clean consistency verdict. See `phase_8_implementation_loop.md`
§ "Four review layers".
