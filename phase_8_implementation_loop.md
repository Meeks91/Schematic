# Phase 8: Implementation Loop

Phase 7 produces `tasks.md`. Phase 8 is the loop that executes each task.

The schematic is the contract; the sketch loop in `~/.claude/CLAUDE.md`
(Plan→Sketch→Confirm→Implement) is the delivery mechanism. The two clauses
in this phase exist to keep that delivery honest:

1. **Cross-cutting concerns must be read before implementing.** Component
   files are self-contained for shape but reference `_overview.md` for the
   *why* behind atomicity, FK invariants, security boundaries, and other
   cross-cutting concerns. Read it before touching code.
2. **Completion is reported through the CLI, not narrated free-text.** The
   CLI forces an explicit answer on whether implementation matched the
   schematic and (if not) whether the schematic was patched to reflect
   reality. No silent "done" allowed.

> [!CAUTION]
> ## NEVER auto-implement tasks. NON-NEGOTIABLE.
>
> Phase 7 may auto-write **task definitions** (the `tasks.md` entries themselves) when the contract is already locked. Phase 8 **implementation** is different: every task goes through the full Plan→Sketch→Confirm→Implement loop from `~/.claude/CLAUDE.md`. The user signed off on the contract, not on the code that implements it. Skipping the sketch gate strips the user of the last review point before code lands on disk.
>
> **Forbidden:** writing implementation code for a task without first presenting a sketch and receiving explicit user confirmation. "The schematic approved the shape" is not consent for the implementation.

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
5. Mark task complete via the CLI:
       schematic-task-done <tag> --matched [y|n] --updated [y|n]
6. Move to next task
```

Step 5 is binding. Marking a task complete by any other mechanism (editing
tasks.md directly, narrating "✓ done" without running the CLI) is forbidden.

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
