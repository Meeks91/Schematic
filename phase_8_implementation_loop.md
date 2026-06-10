# Phase 8: Implementation Loop

Phase 7 produces `tasks.md`. Phase 8 is the loop that executes each task.

The schematic is the contract; the sketch loop in `~/.claude/CLAUDE.md`
(Plan→Sketch→Confirm→Implement) is the delivery mechanism. Four clauses
in this phase keep that delivery honest:

1. **Cross-cutting concerns must be read before implementing.** Component
   files are self-contained for shape but reference `_overview.md` for the
   *why* behind atomicity, FK invariants, security boundaries, and other
   cross-cutting concerns. Read it before touching code.
2. **Implemented code passes a standards review before it can complete.**
   Moving a task to `review` emits a review request; the implementing agent
   launches it as a Sonnet subagent scoped to the task's git diff (see
   "Review gate" below). Findings are resolved and a `clean` verdict recorded
   before completion — the CLI hard-blocks `complete` without it.
3. **Completion is reported through the CLI, not narrated free-text.** The
   CLI forces an explicit answer on whether implementation matched the
   schematic and (if not) whether the schematic was patched to reflect
   reality. No silent "done" allowed.
4. **The phase keeps a MINIMAL completion record: `implementation_report.md`
   at the bundle root.** Record ONLY what required user sign-off: divergences
   from the locked schematic (one dated bullet each), deferred items awaiting
   decision, and commit status — success on everything else is assumed, not
   narrated. Reviews get one line ("Pristine — <rounds>"), not a ledger.
   **Link it from the top of `objective.md`** (one blockquote line) — the
   dashboard renders the bundle, and an unlinked report is invisible there.

> [!CAUTION]
> ## Manual mode NEVER auto-implements. Auto mode is opt-in ONLY.
>
> In **manual mode** (the default) every task goes through the full Plan→Sketch→Confirm→Implement loop from `~/.claude/CLAUDE.md`. **Forbidden:** writing implementation code without first presenting a sketch and receiving explicit user confirmation. "The schematic approved the shape" is not consent for the implementation.
>
> **Auto mode** suspends the per-task sketch gate — but ONLY because the user explicitly entered it via `schematic review start --auto`. It is the single context in which an agent writes implementation code without a per-task sketch. Even then, every task is tested and diff-reviewed as it goes, and the entire feature diff is swept until pristine before the feature is done. **An agent must never select auto mode on its own initiative.**

---

## Two modes — chosen at `review start`

Phase 8 runs in one of two modes, recorded by `schematic review start`:

| Mode | Entry | Per-task delivery | Final pass |
|---|---|---|---|
| **manual** (default) | `schematic review start --schematic <name>` | Plan→Sketch→Confirm→Implement — sketch gate mandatory | per-task review gate |
| **auto** | `schematic review start --auto --goal "<goal>" --schematic <name>` | implement→test→diff-scoped review→fix, no sketch gate | batch-until-pristine sweep over the whole feature diff |

Manual is the default and the safe path. Auto is the user's explicit opt-in to
autonomous implementation; an agent never self-selects it. The per-task protocol
and review gate below apply to **both** modes — manual adds the sketch step in
front; auto omits it and adds the final sweep (see "Auto mode").

---

## Per-task protocol

For each task in `tasks.md`, in order:

```
1. READ the component file at components/<class>.md
2. READ components/_overview.md if this task is flagged as participating in a
   cross-cutting concern (atomicity, security, FK invariant, etc.)
3. Sketch → Confirm → Implement, per ~/.claude/CLAUDE.md sketch loop.
   NO AUTO-IMPLEMENTATION. The sketch gate is mandatory regardless of how
   small or mechanical the task appears.
4. Run tests (the new tests for this class AND the full suite at milestones)
5. Move the task to REVIEW — this emits the review request:
       schematic task status <tag> review --schematic <name>
   Launch the printed prompt as a Sonnet subagent (Agent tool), then record
   the verdict:
       schematic task review-result <tag> clean|findings --summary "<one line>" --schematic <name>
   See "Review gate" below. The task CANNOT complete until the recorded
   verdict is clean.
6. Resolve review findings: address every note the review agent leaves, then
   re-run tests. Re-trigger step 5 if you changed code.
7. Mark task complete via the CLI (drift report) once the verdict is clean:
       schematic-task-done <tag> --matched [y|n] --updated [y|n]
8. Move to next task
```

Steps 5 and 7 are binding. Completing a task that never passed through `review`,
or by any mechanism other than the CLI (editing tasks.md directly, narrating
"✓ done"), is forbidden.

---

## Review gate (Step 5 — standards verification)

Moving a task to `review` is the gate between "code written" and "task done".
It exists to verify the **written code adheres to the resolved standards** before it locks.

```
schematic task status <tag> review --schematic <name>
```

**Dispatch model: the CLI is the gatekeeper, the session agent is the
dispatcher.** On that transition the CLI records a `review_request` and prints
the review prompt; the **implementing agent** launches it as a Sonnet subagent
via its Agent tool (in-session — so the dispatcher can prepend known
sanctioned patterns and prior false-positive rulings to the prompt). The CLI
never spawns `claude -p` itself.

**Scope: the git diff ONLY.** The reviewer reads `git diff HEAD` /
`git status --short`, intersects the changed files with the task's component
spec, and reviews **only added/modified lines**. Pre-existing code — even in
the same file, even verbatim-moved code — is out of scope and must never be
flagged: findings on unchanged code are false flags by definition. Primary
lens is the resolved standards modules (styling + testing for the task's
language, plus the project's CLAUDE.md). The review runs on Sonnet (scoped +
cheap), not the session's planning model.

Protocol:

1. **Request** — `task status <tag> review` records a `review_request`
   (status: pending) and prints the diff-scoped review prompt.
2. **Dispatch** — the implementing agent launches the prompt as a Sonnet
   subagent (Agent tool). Never skip; never review your own code inline
   instead.
3. **Findings land as notes** — the review agent records each finding via
   `schematic task note <tag> "<finding>"` and ends with `VERDICT: clean` or
   `VERDICT: findings`. It does **not** self-complete the task.
4. **Record** — the implementing agent records the verdict:
   `schematic task review-result <tag> clean|findings --summary "<one line>"`.
5. **Resolve** — on `findings`: fix every note through the normal sketch loop,
   re-run tests, re-dispatch from step 1.
6. **Complete** — only once the recorded verdict is `clean`, run
   `schematic-task-done` (below). Both `schematic task complete` and
   `schematic-task-done` hard-block without a clean verdict (`--override` /
   `--force` are the explicit, recorded escape hatches).

The review gate verifies standards; `schematic-task-done` records schematic
drift. Both run — neither replaces the other.

---

## Auto mode — driver loop + batch-until-pristine sweep

Entered by `schematic review start --auto --goal "<goal>" --schematic <name>`,
which records the mode and pins `base_ref` to the current HEAD. An agent never
enters this mode on its own — only the user runs that command.

### Driver loop (per task, NO sketch gate)

```
while `schematic task next` returns a task:
  1. READ the component file (+ _overview.md if a cross-cutting concern is flagged)
  2. implement the task directly — no sketch, no confirm
  3. run its tests + the full suite at milestones
  4. per-task review gate, diff-scoped to THIS task only:
       schematic task status <tag> review        → dispatch Sonnet subagent on the task's diff
       schematic task review-result <tag> clean|findings --summary "..."
     fix findings, re-dispatch until clean
  5. schematic-task-done <tag> --matched [y|n] --updated [y|n]
```

The per-task review here is the same gate as manual mode — scoped to that one
task's diff. Auto mode only removes the sketch step in front of implementation.

### Final sweep (batch-until-pristine)

Once the board is drained, sweep the WHOLE feature diff until it returns clean:

```
schematic review sweep --schematic <name>
```

Each sweep computes the cumulative diff since `base_ref` (feature files only —
the `docs/schematics/` planning tree is excluded), shards it into batches of at
most **5 files**, and prints one review prompt per batch. For each batch the
implementing agent launches a Sonnet subagent (Agent tool) on the printed
prompt. Every prompt carries three HARD RULES:

1. **Read ONLY the ≤5 listed files** — never open, grep, or read anything else.
   This is the token bound; reading outside the batch blows the budget.
2. **Flag ONLY lines added/modified vs `base_ref`** — pre-existing or unchanged
   code, even in these files, is out of scope and a false flag.
3. **Never flag or edit code outside the feature.**

Lens: the resolved `review`-slot module if the manifest maps one, else the
resolved styling + testing modules for each file's language.

Record each batch, then fix and re-sweep:

```
schematic review batch-result <batch_id> clean|findings --summary "<one line>" --schematic <name>
```

Fix every finding, then **re-run `review sweep`** — a fresh sweep over the new
diff. Repeat until a sweep reports `PRISTINE` (every batch clean). The feature
is not done until a pristine sweep exists. `schematic review status` shows the
mode, `base_ref`, and the latest sweep's per-batch verdicts.

---

## Completion CLI

Located at `~/.claude/skills/schematic/scripts/schematic-task-done` (symlinked onto PATH as `schematic-task-done`).

Usage:

```
schematic-task-done <tag> --matched [y|n] --updated [y|n] [--tasks-file PATH]
```

Arguments:

- `<tag>` — the canonical task tag from `tasks.md` (e.g. `b.6`, `c.3`, `a.2`).
- `--matched y|n` — did the implementation match the component file exactly
  (constructor, method names, signatures, models, errors)?
- `--updated y|n` — if `--matched=n`, did you update the component file to
  reflect what you actually built?
- `--tasks-file` — optional, defaults to `tasks.md` in CWD. Use when running
  from a directory that isn't the schematic root.

Behaviour:

| matched | updated | Result                                                          |
|---------|---------|-----------------------------------------------------------------|
| y       | y       | Mark complete. No divergence line written.                      |
| y       | n       | Mark complete. (No divergence to update.)                       |
| n       | y       | Mark complete. Append `Divergence: patched-in-component-file`. |
| n       | n       | Mark complete. Append `Divergence: bridged-not-patched` flag.   |

The `n / n` case is allowed — sometimes a bridge is the right call — but it
puts a flag on the task entry so the next agent knows to expect divergence.

The CLI exits non-zero if:
- the tag is not found in `tasks.md`
- required flags are missing
- the task is already marked complete (re-running requires `--force`)
- no `clean` review verdict is recorded in `.schematic-state.json` for the tag
  (bypassing requires `--force`)

---

## Cross-cutting concerns — when to read `_overview.md`

Component files name a class's responsibility and contracts. The *why*
behind cross-cutting concerns lives in `_overview.md`. Read it before
implementing any component flagged with:

- **Atomicity** — participates in a transaction that spans multiple repos
- **FK invariant** — assumes an FK guarantees a sibling row exists
- **Security boundary** — verifies/authorizes a request from outside the trust zone
- **Cache coherence** — reads/writes through a shared cache layer
- **Idempotency** — must produce the same result on re-call with same input

A component file SHOULD flag these at the top via a single line:

```
Cross-cutting: atomicity (see _overview.md §<section>)
```

If the flag is missing but the AC text implies one of these concerns, read
`_overview.md` anyway. Better to over-read than ship a security boundary
that violates the project's threat model because rationale lived elsewhere.

---

## Blueprint Drift Validation (post-all-tasks)

After every task is marked complete, walk the schematic vs the code and
verify they still match. Per-task CLI calls catch per-task drift; this
post-flight catches:

- **Topology drift** — classes added/removed/renamed without `objective.md`
  catching up
- **Sequence drift** — actual call flow vs `sequence.mmd`
- **DAG drift** — constructor wiring vs `dag.mmd`
- **Contract drift** — signature changes that the per-task CLI marked as
  divergent-not-patched

For any drift found: update the schematic files to match reality (with
user sign-off). The schematic is the final record of what was built.
