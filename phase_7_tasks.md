# Phase 7: Tasks + Implementation

> **CLI gate commands:**
> - `schematic phase audit --schematic <name> 7 "clean" | "<findings>"` — after end-to-end audit returns.
> - `schematic milestone decide yes|no --schematic <name>` — the milestone question, asked immediately after the task-graph `y`. **`phase complete 7` REFUSES until this is recorded.**
> - `schematic milestone propose --schematic <name>` → `schematic milestone lock --schematic <name>` — on `yes` only: validate the proposed table, then lock it on the user's `y`.
> - `schematic phase sign-off --schematic <name> 7` — on user `y`.
> - `schematic phase complete --schematic <name> 7` — immediately after sign-off.
> - `schematic task show|status|complete|next` — drive the Phase 8 implementation loop (see `phase_8_implementation_loop.md`).
> - `schematic validate` — final AC-pyramid + cross-ref integrity check before handing off to implementation.

Write all tasks to `<schematic_dir>/tasks.md`.

Each task must be self-contained enough for a cold-start agent. Each task includes:

- **Feature ACs** it satisfies (by number from `objective.md`)
- **Class AC** (from `components/_overview.md` component summary)
- **Function ACs** (from `components/<class>.md`)
- **Constructor dependencies** (from `components/<class>.md`)
- **Integration point** (from `components/_overview.md`)
- **Test hierarchy**: AC Tests (primary) + Branch Tests (secondary) — referenced from `components/<class>.md`

Use the `tasks.md` format defined in `SKILL.md` → Schematic File Structure.

## Task graph overview (BINDING — present BEFORE Phase 7 gates)

Before writing `tasks.md` and starting per-gate task locks, surface the complete task graph to the user as one scannable artifact. This grounds the user in the *what* + *why* + *blocking dependencies* across the whole feature before details begin to dominate.

**Format (binding — every Phase 7 must use this shape):**

- One Markdown table per dependency **group** (A, B, C, ...). Groups bundle tasks that share a common driving theme (e.g. "Foundations", "Production analyser stack", "Eval framework"). The user reads top-to-bottom and sees how the build composes.
- Each table has **exactly five columns**, in this order:

  | Column     | Content                                                                                  |
  |------------|------------------------------------------------------------------------------------------|
  | `Tag`      | `<group-letter>.<index>` (e.g. `a.1`, `b.3`). Stable identifier — never renumber.        |
  | `Action`   | One of `Create`, `Modify`, `Rename`, `Tighten`, `Delete`, `Wire`, `Add`, `Split`.        |
  | `Target`   | Fully-qualified class, file path, or `ClassName.method`. Backticked for monospace.       |
  | `Purpose`  | One sentence — what this task achieves and **why**. No "implements AC-3.B" tags; describe the outcome in plain language so the user stays present in intent. |
  | `Deps`     | Comma-separated list of tag IDs that block this task, or `—` if free. Order = exec order.|

- After the last group table, render the **critical-path chain(s)** as a fenced ASCII block. Show one chain per coherent ship-line (e.g. one for production, one for eval). Format:
  ```
  Production:  a.1, a.2 → b.1, b.2 → b.3 → b.4 → c.3   (ship-ready)
  Eval:        a.1, d.1 → d.2 → d.5, d.6 → d.8         (eval CLI runnable)
  ```
  The annotation in parentheses names what the chain *delivers* — same purpose-first principle as the Purpose column.

- Banned: inline parentheticals appended to rows (e.g. `Create | Foo (does X, Y, Z) | b.1, b.2`). They blow the column rhythm and force the reader to parse prose where they should be scanning a grid. Put detail in the Purpose column or in a footnote line below the table.

**Why this shape (skill purpose anchor):** The grid lets the user verify the dependency DAG, ordering, and ship-line composition at a glance — every cell answers one question, and the Purpose column keeps the *why* present alongside the *what*. After this graph is approved, per-gate task locks fill in contracts/tests; the grid is the map the user holds throughout.

Present the full graph for sign-off **before** writing any detailed blocks. The graph is the ONLY gated artifact in Phase 7.

**Detailed task blocks are auto-written (no per-gate sign-off).** On the graph `y`, write the graph as the header of `tasks.md` and then write ALL detailed task blocks in one pass. Rationale: every Feature AC, Class AC, Function AC, contract, dependency, and test was already gathered and signed off in Phases 1–6 — the detailed block is a pure mechanical projection of the locked `components/<class>.md` cards onto the task skeleton. Re-gating it at ≤3/gate re-litigates already-approved content and adds no decision. The graph (deps, ordering, ship-lines) is where the user's judgement is needed; the blocks are derivation. After writing all blocks, run the end-to-end audit and present the whole `tasks.md` for the single Phase-7 content lock.

## Milestones (BINDING step — asked immediately after the graph `y`)

The graph `y` is the moment the user can see the whole shape of the build. Ask, in one line, before any detailed block is written:

> **Question:** Split this task set into a multi-stage delivery using milestones?
> **Why:** a milestone stops the build at a checkpoint you sign off, instead of running to the end in one pass.

Record the answer through the CLI — it is the state of record, and `schematic phase complete 7` refuses without it:

```
schematic milestone decide yes|no --schematic <name>
```

**`no`** — delivery is exactly as it has always been: one implicit milestone, no boundary, no gate. Nothing else in the bundle changes. Proceed to the audit hook.

**`yes`** — propose milestones over the graph's **groups** (never over individual tasks unless one must be pulled forward) as a `## Milestones` table written into `tasks.md` directly beneath the task graph:

```markdown
## Milestones

| Milestone | Title | Scope | Proves |
|---|---|---|---|
| M1 | Resolver reachable | a, b | A caption-miss returns provider text through the real client. |
| M2 | Recovery wired and persisted | c, d | An ingestion run stores a recovered transcript with its source. |
| M3 | Composition and live probe | e, f | Every root builds; the paid probe returns text. |
```

- **Ids** run `M1, M2, …` in table order; the order IS the delivery order.
- **Scope** takes group letters (`a`) and/or explicit task tags (`c.1`). An explicit tag beats a group letter that would also claim the task — that is how one task gets pulled into an earlier stage without splitting its group.
- **Proves** is the whole point of the row: what the user can *see working* when that stage lands. A milestone that proves nothing observable is a milestone in name only — fold it into its neighbour.
- Every task must belong to **exactly one** milestone, and no task may depend on a task in a **later** one. Both rules are mechanical: before lock, `schematic milestone propose` (and `lock`) refuses, printing the offending tags — `schematic validate` does NOT check a table until it is locked; after lock, `schematic validate` keeps failing for as long as the table is wrong.
- The section holds the table and nothing else — footnotes go under the graph.

Then gate it, in this order:

```
schematic milestone propose --schematic <name>   # prints the RESOLVED membership: which tasks each stage claims
                                                 # present that output — the user gates on membership, not on prose
schematic milestone lock --schematic <name>      # on the user's y
```

**Post-lock re-scope is an amendment, never a hand-edit:** `schematic milestone amend --schematic <name> --move <tags> --to M<n> --reason "<why>"` (or `--add M<n> --title … --scope … --proves …`). It rewrites the table, expanding a group letter into its remaining tags when one leaves, and records the delta in state.

## Detailed task block shape (BINDING)

Every detail block under `## Detailed Task Blocks` MUST use this skeleton:

```
## <tag> | <Action> | <Target>

Status: pending
Component file: components/<class>.md
Blocked by: <tag>, <tag>   (or "—" if none)

**Feature ACs:** <ref> — <title>, <ref> — <title>
**Class AC:** see `objective.md` §<n>

**Scope:**
- bullets

**Test files (NEW):** <paths or "none — <reason>">
```

- **Heading MUST be H2 (`## <tag> | <Action> | <Target>`).** The CLI parser is `^## ([a-z]\.\d+) \| (\w+) \| (.+)$` — H3 (`###`) does NOT match and the task becomes invisible to `schematic task next/show/status`. `<Action>` must be a single word (`\w+`) from the canonical verb list in `SKILL.md` → Cross-reference naming rule (`Create`/`Modify`/`Rename`/`Tighten`/`Delete`/`Wire`/`Add`/`Split`). Task H2s sit beneath the `## Detailed Task Blocks` H2 — that section header has no ` | ` so the parser skips it.
- **`Status: pending`** is mandatory — the CLI flips it to `complete` and refuses to operate on blocks missing it.
- **`Component file:`** (CLI key, bare — not `**Contract:**`) gives the agent its contract card and is existence-checked by `schematic validate`. OMIT the line for tasks with no card (migrations, deletions, composition root, smoke test) — a dangling path fails validate.
- **`Blocked by:`** (CLI key, bare) drives `schematic task next` ordering; list the dependency tags or `—`. Must mirror the graph's Deps column exactly. Tags here that aren't real task tags fail validate.
- These three bare keys (`Component file:`, `Blocked by:`, `Status:`) are the only CLI-parsed lines an author writes; everything else (`**Feature ACs:**`, `**Class AC:**`, `**Scope:**`, `**Test files (NEW):**`) is human context the CLI ignores. A fourth bare key, `Divergence:`, is written by `schematic-task-done` on completion and read back into the milestone report — never author it by hand.

## Audit hook (mandatory — at end of Phase 7, after all task gates locked)

After every Phase 7 task gate is locked, dispatch the end-to-end audit — it walks the entire schematic (objective, components, DAG, sequence, tasks) and verifies consistent cross-references, no orphans, complete AC pyramid.

1. Dispatch `audits/end_to_end_audit.md` per `audits/README.md`. Wait for return. Surface findings above sigil.
2. Record: `schematic phase audit --schematic <name> 7 "clean" | "<findings>"`

**Confirm: y/comment**

---

## Implementation

Phase 7 ends when `tasks.md` is locked. Implementation happens in **Phase 8**.

See `phase_8_implementation_loop.md` for:
- Per-task protocol (read component file + `_overview.md` for cross-cutting concerns)
- The `schematic-task-done` CLI used to mark tasks complete with honest divergence reporting
- Post-all-tasks blueprint drift validation

Either flow (collaborative sketch loop or autonomous execution) is valid — the
schematic is designed so any agent can pick up `tasks.md` + the referenced
`components/<class>.md` file and implement cold. Phase 8 covers both.
