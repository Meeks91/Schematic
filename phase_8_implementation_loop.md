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
   launches it as a review-model subagent (`schematic.reviewModel` in
   `standards.json`, default `sonnet`) scoped to the task's git diff (see
   "Review gate" below). Findings are resolved and a `clean` verdict recorded
   before completion — the CLI hard-blocks `complete` without it.
3. **Completion is reported through the CLI, not narrated free-text.** The
   CLI forces an explicit answer on whether implementation matched the
   schematic and (if not) whether the schematic was patched to reflect
   reality. No silent "done" allowed.
4. **The phase keeps a MINIMAL completion record: `implementation_report.md`
   at the bundle root.** It holds only what the user must know to ship the
   feature — the functional and behavioural changes that diverged from the
   locked schematic (one dated bullet each), deferred items awaiting decision,
   and commit status; never run history, review rounds, or the CLI's own ledger.
   **Link it from the top of `objective.md`** (one blockquote line) — the
   dashboard renders the bundle, and an unlinked report is invisible there.
5. **Independent decisions are logged, then signed off at the end.** Any decision
   made during implementation that the schematic didn't answer AND that no user
   sketch gate approved is recorded to the decision ledger the moment it's made.
   At end-of-impl these are presented as a batch for user sign-off and folded into
   the completion record. See "Decision ledger (both modes)" below.
6. **A note is not a state.** A decision the design does not answer is not resolved by
   annotating a card, a report, or a commit message. The agent files a question and the
   CLI holds the task:

   ```
   schematic task ask <tag> "<question> — why: <what is blocked>"
   ```

   That moves the task to `pendingInput` and files the question in the same Q&A relay
   the dashboard bubble uses. The user answers with `schematic answer <id> "<text>"`,
   which returns the task to `in_progress`. The CLI refuses `task complete` and
   `task status <tag> review` while any question on the task is unanswered — and
   `--override` does NOT close one. `validate` fails on any task in `pendingInput`,
   on any unanswered question, and on ratification prose ("awaiting ratification",
   "needs sign-off") sitting in a card or ledger with no question behind it.

> [!CAUTION]
> ## Manual mode NEVER auto-implements. Auto mode is opt-in ONLY.
>
> In **manual mode** (the default) every task goes through the full Plan→Sketch→Confirm→Implement loop from `~/.claude/CLAUDE.md`. **Forbidden:** writing implementation code without first presenting a sketch and receiving explicit user confirmation. "The schematic approved the shape" is not consent for the implementation.
>
> **Auto mode** suspends the per-task sketch gate — but ONLY because the user explicitly entered it via `schematic review start --auto`. It is the single context in which an agent writes implementation code without a per-task sketch. Even then, every task is tested and diff-reviewed as it goes, each task group is standards-swept to PRISTINE as it drains, and the whole feature diff gets a final consistency pass and entry-point tracing before the feature is done. **An agent must never select auto mode on its own initiative.**
>
> **Auto mode STOPS on `pendingInput`.** Auto suspends confirmation gates, never the need for a human where the design is silent. The moment a task hits a decision the schematic does not answer and that is not a bare naming or placement choice, the agent runs `schematic task ask` and that task is done being worked. Auto continues on OTHER unblocked tasks; it never guesses on the held one, never marks it complete, and never resumes it by writing its own answer. If every remaining task is held, auto surfaces the open questions and stops — exactly as it already stops on `schematic questions`.

---

## Two modes — chosen at `review start`

Phase 8 runs in one of two modes, recorded by `schematic review start`:

| Mode | Entry | Per-task delivery | Final pass |
|---|---|---|---|
| **manual** (default) | `schematic review start --schematic <name>` | Plan→Sketch→Confirm→Implement — sketch gate mandatory | per-task review gate |
| **auto** | `schematic review start --auto --goal "<goal>" --schematic <name>` | implement→test→diff-scoped review→fix, no sketch gate | per-group standards sweep → consistency → e2e entry-point tracing |

Manual is the default and the safe path. Auto is the user's explicit opt-in to
autonomous implementation; an agent never self-selects it. The per-task protocol
and review gate below apply to **both** modes — manual adds the sketch step in
front; auto omits it and adds the per-group standards sweep, the consistency pass, and entry-point tracing (see "Auto mode").

---

## Per-task protocol

For each task in `tasks.md`, in order:

```
1. CLAIM the task:
       schematic task next --schematic <name>
   This shows the task AND moves it to in_progress atomically.
   (Use --peek to inspect without claiming.)
2. READ the component file at components/<class>.md
3. READ components/_overview.md if this task is flagged as participating in a
   cross-cutting concern (atomicity, security, FK invariant, etc.)
4. Sketch → Confirm → Implement, per ~/.claude/CLAUDE.md sketch loop.
   NO AUTO-IMPLEMENTATION. The sketch gate is mandatory regardless of how
   small or mechanical the task appears.
5. Run tests (the new tests for this class AND the full suite at each milestone boundary)
6. Move the task to REVIEW — this emits the review request:
       schematic task status <tag> review --schematic <name>
   Launch the printed prompt as a review-model subagent (Agent tool), then record
   the verdict:
       schematic task review-result <tag> clean|findings --summary "<one line>" --schematic <name>
   See "Review gate" below. The task CANNOT complete until the recorded
   verdict is clean.
7. Resolve review findings: address every note the review agent leaves, then
   re-run tests. Re-trigger step 6 if you changed code.
8. Mark task complete via the CLI (drift report) once the verdict is clean:
       schematic-task-done <tag> --matched [y|n] --updated [y|n]
9. Move to next task
```

**Blast-radius trigger (binding):** if the task modified an EXISTING public contract
(new or changed result-determining input), run the Integration & Blast Radius lens
(resolved review module) BEFORE requesting review — grep dependents + derived-key
sites (cache/memo/dedupe/etag/hash/`__eq__`); every determining input must appear in
every derived key. Applies in both modes; greenfield tasks skip it.

**Meeting-point inventory (binding):** a ruling or a task that touches an identity,
a casing/canonical form, a time bound, or a state vocabulary must carry a
grep-derived inventory of EVERY site that mints or compares that value — writers,
readers, and the source the value comes from — written BEFORE its test list. No
inventory, no test list: an agreement fixed on one side only is the defect this
catches, and each side's own unit tests pass while it is broken.

**Ship-ready rule (binding):** a task may be submitted for review only with **zero open
questions** and zero as-built amendments awaiting anything. "Built, but X is still open"
is not a reviewable state — it is a `pendingInput` state. Ask, get the answer, then
submit. The CLI enforces this: `task status <tag> review` is refused while a question on
the task is unanswered.

Steps 1, 6, and 8 are binding. Starting implementation without `task next` having
moved the task to `in_progress`, completing a task that never passed through
`review`, or completing by any mechanism other than the CLI (editing tasks.md
directly, narrating "✓ done"), is forbidden.

---

## Decision ledger (both modes — binding)

Every decision the schematic doesn't answer **and** that no user sketch gate
approved is recorded at the moment it's made:

```
schematic task decision <tag> "<what> — <why>" --kind naming|placement
```

**The ledger's scope is narrow, and the CLI enforces it.** `task decision` takes
`--kind naming|placement` and accepts nothing else. Those are the only choices an agent
may take alone: what to call a thing, and where to put it. Anything that

- changes a signed contract (signature, model field, error, return shape), or
- adds a caveat, a known-wrong path, or a "works except when…", or
- picks a value the card did not specify (a threshold, a window, a page size, a key)

is **not a decision — it is a question.** Use `schematic task ask`. Recording such a
choice as a decision and continuing is the exact failure this rule exists to stop: the
task reaches `complete` carrying a defect the design never sanctioned.

- **Manual mode** — the sketch gate covers most choices; the ledger captures the
  residue (calls the sketch didn't cover, made independently of the user).
- **Auto mode** — captures every unanswered decision.

**End-of-impl sign-off (manual):** before the feature is done, present the ledger as
a batch with `Confirm: y/comment`; the user signs off each decision, folded into
`implementation_report.md` § **Autonomous decisions** (strategic entries →
`objective.md` § Decision Log). Auto mode folds it in at the e2e gate — no
per-decision gate.

A decision not in the ledger didn't happen — silent improvisation is forbidden.

---

## Review gate (Step 5 — standards verification)

Moving a task to `review` is the gate between "code written" and "task done".
It exists to verify the **written code adheres to the resolved standards** before it locks.
The gate runs TWO lenses: (1) standards conformance, (2) task-level correctness against the
component spec — checklist content comes from the manifest-resolved modules (`review` slot),
never restated here.

```
schematic task status <tag> review --schematic <name>
```

**Dispatch model: the CLI is the gatekeeper, the session agent is the
dispatcher.** On that transition the CLI records a `review_request` and prints
the review prompt; the **implementing agent** launches it as a review-model subagent
via its Agent tool (in-session — so the dispatcher can prepend known
sanctioned patterns and prior false-positive rulings to the prompt). The CLI
never spawns `claude -p` itself.

**Scope: the git diff ONLY.** The reviewer reads `git diff HEAD` /
`git status --short`, intersects the changed files with the task's component
spec, and reviews **only added/modified lines**. Pre-existing code — even in
the same file, even verbatim-moved code — is out of scope and must never be
flagged: findings on unchanged code are false flags by definition. Primary
lens is the resolved standards modules — the CLI resolves and lists their
exact paths in the printed prompt (styling + testing for the task's language,
the `review` module if mapped, plus the project's CLAUDE.md, which overrides
on conflict). The review runs on the configured review model
(`schematic.reviewModel`, default `sonnet`), not the session's planning model.

Protocol:

1. **Request** — `task status <tag> review` records a `review_request`
   (status: pending) and prints the diff-scoped review prompt.
2. **Dispatch** — the implementing agent launches the prompt as a review-model
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

**Reviewer rule — an open question is a FAIL, never a note (binding).** If a reviewer
finds, anywhere in scope, an unanswered question, a caveat, a "pending ratification" /
"needs sign-off" annotation, or a known-wrong path the card does not sanction, the verdict
is `VERDICT: findings` — not a clean verdict with a remark attached. A reviewer that
passes work while recording the caveat has converted a blocking defect into prose, which
is the failure mode this gate exists to prevent. The correct resolution is
`schematic task ask`, by the implementing agent, before the task returns to review.

The review gate verifies standards; `schematic-task-done` records schematic
drift. Both run — neither replaces the other.

---

## Auto mode — driver loop + per-group standards sweep + final review (consistency · entry-point tracing)

Entered by `schematic review start --auto --goal "<goal>" --schematic <name>`,
which records the mode and pins `base_ref` to the current HEAD. An agent never
enters this mode on its own — only the user runs that command.

### Driver loop (per task, NO sketch gate)

```
while `schematic task next` returns a task:
  1. READ the component file (+ _overview.md if a cross-cutting concern is flagged)
  2. implement the task directly — no sketch, no confirm
  3. run its tests + the full suite at each milestone boundary
  4. per-task review gate, diff-scoped to THIS task only:
       schematic task status <tag> review        → dispatch review-model subagent on the task's diff
       schematic task review-result <tag> clean|findings --summary "..."
     fix findings, re-dispatch until clean
  5. schematic-task-done <tag> --matched [y|n] --updated [y|n]
```

The per-task review here is the same gate as manual mode — scoped to that one
task's diff. Auto mode only removes the sketch step in front of implementation.

**The loop exits at a milestone boundary by construction.** When the bundle declares
milestones, `schematic task next` serves nothing from milestone n+1 until milestone n is
signed off — so the `while` condition simply stops being true at the boundary. There is no
"remember to stop" instruction that can be forgotten. See "Milestone boundary" below.

**Decision ledger (mandatory):** see "Decision ledger (both modes)" above — auto
mode records every unanswered decision via `schematic task decision <tag> "<what> —
<why>"`. The e2e gate prints the collected ledger; the master folds it into
`implementation_report.md` § **Autonomous decisions**.

### Four review layers (auto mode)

```
#1  per-task review      one task's diff        standards + correctness   loops to clean       per task (driver loop above)
#2  standards sweep      a group's files, ≤5s   standards                 loops to PRISTINE    per GROUP boundary
#3  consistency sweep    whole diff, one agent  duplication/redundancy    single pass, NO loop feature end
#4  entry-point tracing  per entry point        correctness (ACs)         no loop              feature end
```

`#1` is the driver loop's per-task gate above. `#2` runs each time a task group
completes; `#3` and `#4` run once the board is drained.

**Where the layers close when milestones are declared (binding split).** `#1` and `#2` are
**per-milestone** — `schematic milestone sign-off` refuses unless every task in the stage holds
a clean per-task verdict AND (in auto mode) a sweep stamped with that milestone recorded
PRISTINE. `#3` and `#4` stay at **feature end**, unchanged, because both read properties a
partial diff cannot show: duplication is a cross-file property of the whole change set, and
entry-point tracing reads the finished system (a stage's entry point may be rewritten by a
later stage). A milestone sign-off is therefore "this stage is built to standard", never "this
stage is correct end to end".

In **manual mode** there is no sweep to record — `review sweep` is an auto-mode command — so
sign-off requires only the per-task verdicts, and the CLI says so on the sign-off line rather
than implying a sweep happened.

### Milestone boundary (when the last task of a stage completes)

`schematic task next` finds nothing servable, detects that the open milestone is fully
complete, and does three things in one breath:

1. writes/refreshes that milestone's section of `implementation_report.md` — tasks with their
   divergence flags, the autonomous decisions recorded against them, each task's review
   verdict and summary, the sweep result, the suite's last lines (if recorded), and every open
   `task ask` question belonging to the stage;
2. prints the section, so the terminal holds the report regardless of the browser;
3. opens the dashboard on that milestone's Reports entry (fail-closed: the command exits 1 if the
   dashboard never reports a URL). Set `SCHEMATIC_NO_BROWSER=1` to skip the launch — unattended
   or CI runs; the report is still written and printed.

Then it stops. **Present the report and STOP** — the user rules on the stage:

```
schematic milestone report M<n> --schematic <name> [--suite "<suite last lines>"]   # re-read / record suite output
schematic milestone sign-off M<n> --schematic <name>                               # on the user's y → opens M<n+1>
```

`--suite` is how the suite's last lines reach the report; without it the section reads
`not recorded` rather than pretending. Sign-off refuses while any task of the stage is
incomplete or `pendingInput`, while any task lacks a clean review, while an earlier milestone
is unsigned, and — in auto mode — until its groups are swept PRISTINE. `schematic phase
complete 8` refuses while any milestone is unsigned (`--override "<reason>"` records the
exception). On the Phase-8 lock the CLI opens the dashboard on the finished bundle — non-fatal:
the lock is already saved, so a dashboard that never starts only prints a warning and the
`schematic overview <name>` command to run by hand. `SCHEMATIC_NO_BROWSER=1` skips it here too.

### #2 — per-group standards sweep

As each task GROUP (`a.`, `b.`, `c.`, …) drains, run the sweep over what that group touched:

```
schematic review sweep --schematic <name>
```

The sweep computes the cumulative diff since `base_ref` (feature files only — the
`docs/schematics/` planning tree is excluded), shards it into batches of at most
**5 files**, and prints one **STYLE + STANDARDS** review prompt per batch, with the
resolved standards modules inlined. **Per-group scoping falls out of timing + the skip,
not a flag:** at group `a`'s boundary the cumulative diff is only `a`'s files; at group
`b`'s boundary the skip drops `a`'s already-clean files and only `b`'s new files re-enter
batches. No `--group` argument — the CLI can't map a group to file paths (task targets are
prose), and it doesn't need to.

**Diff-only prompts — agents see diff hunks, not full files.** The CLI inlines
`git diff base_ref -- <batch files>` and the resolved standards module content
(styling + testing for the batch's languages) directly into the prompt. Agents
receive all input inline and do NOT read any files. This structurally eliminates
false positives from pre-existing code — agents literally cannot see it.

**Triggered lenses.** A resolved review module may carry a lens scoped to part of the
codebase, declared by a `Triggers:` line of path globs directly under its heading. The CLI
does no matching — it inlines every resolved review module, in manifest order, under its
own `── review (<source>) ──` header. The reviewing agent applies a triggered lens **only
when a path in its batch matches that lens's globs**, and applies its FAIL conditions
verbatim when it does. (The same lenses fire at planning time from the Phase 7 audit,
against task target paths instead of diff paths.)

Every prompt carries three HARD RULES:

1. **Do NOT read, open, or grep ANY files** — the diff below is the ONLY input.
2. **Flag ONLY lines that appear as added (+) or modified in the diff** —
   pre-existing context lines are OUT of scope and a false flag.
3. **Never flag or edit code outside the feature.**

Record each batch, then fix and re-sweep:

```
schematic review batch-result <batch_id> clean|findings --summary "<one line>" --schematic <name>
```

Fix findings, re-sweep until PRISTINE (every batch clean). **Re-sweeps are incremental
(token discipline):** a file whose diff is byte-identical to one already reviewed `clean`
in a prior sweep is skipped and logged — only re-touched files re-enter batches. A re-sweep
where every file is skipped reports PRISTINE immediately. This is the mechanic that scopes
each sweep to its group.

### #3 — consistency sweep (single agent, one pass)

Once every group is swept PRISTINE and the board is drained:

```
schematic review consistency --schematic <name>
```

ONE review-model agent over the ENTIRE feature diff in a single view, **one pass, no
loop**, asking only: what is duplicated, what is redundant, what says the same thing two
ways (names, patterns, helpers) across files and tasks. It does NOT loop — re-running a
reviewer over signed-off code chasing names and patterns is the churn `#1` and `#2` already
own; this pass reads once. Standards are NOT re-checked — the earlier gates held them.
Duplication is a cross-file property, so this pass needs the whole diff in one view (a
5-file shard cannot see a helper duplicated eight files away).

Plus a **mechanical per-file line-limit check**: the CLI itself flags any Python feature
file whose logic lines (imports excluded) exceed the ceiling (`schematic.maxFileLines`,
default 220) — no subagent, no standards read. The master splits or justifies each.

The master triages findings with full context (a locked card or ledgered ruling beats the
reviewer), fixes the accepted ones, and records the verdict. Plus the project's whole-tree
gates (linter, type checker, full suites — whatever its own config declares) run once.

```
schematic review consistency-result clean|findings --summary "<one line>" --schematic <name>
```

### #4 — e2e entry-point tracing (adversarial)

Requires a clean consistency gate. `#2`/`#3` read the diff; `#4` reads the **system**, and
it is the only pass that can catch a defect whose whole nature is that nothing in the diff
looks wrong — a runner that will happily apply a file a comment says to hold back, a
scheduled job that fires against something a later step removes, a flag whose meaning
drifted between two entry points.

```
schematic review e2e --schematic <name>
```

One **correctness-model reviewer per entry point** (`schematic.correctnessModel` in
`standards.json`; default = the session's planning model, never `reviewModel`), run in
parallel. "Entry point" explicitly includes *operational* entry points, not just the
feature's own API surface:

- every HTTP route / MCP tool / public service method the feature adds or changes
- **any runner that applies files from a directory** (schema migrations, seed
  scripts, jobs) — what it globs, what it skips, what one `--yes` covers
- **the deploy commands** — what each subcommand actually executes, with which args
- **the cron / scheduled / workflow entrypoints** — including anything registered
  in another database or another system (pg_cron, Cloud Scheduler, terraform)

Each reviewer traces its entry point **all the way to storage and back**, against the ACs
as the oracle, and must produce **cross-path claims** — statements about what a *different*
entry point now does as a consequence. A finding that only restates its own path is not a
finding; the value is entirely in the crossings ("the scheduled job in database A calls a
function the chain for database B deletes", "the deploy job passes `--yes`, which this
change makes sufficient to drop a table"). Each reviewer carries the 7 checks: wiring,
contracts, test coverage, integration, correctness, blast radius, and the **meeting-point
inventory table** (state · writer file:line · reader file:line · axes · e2e test) — an
empty inventory on a feature touching SQL or a shared model is a FAIL, not clean.

Then **one correctness-model reconciler** reads every reviewer's output, dedupes, resolves
contradictions, and ranks by blast radius. Output goes to
`research/correctness_pass_<date>/` under the schematic:

```
research/correctness_pass_2026-09-03/
  R1_<entry_point>.md            one per reviewer
  R2_<entry_point>.md
  ...
  R_reconciled.md                the reconciler's single ordered list
  R_dispositions.md              the addendum, written as the user rules on each
```

**Findings are user-dispositioned, never auto-fixed** — including in auto mode. `#4` is a
*reading* pass; the agent presents `R_reconciled.md` and stops. The user decides per
finding: fix now, fix later (with a named home), or accept. The dispositions addendum
records that ruling. An agent that silently fixes a finding has destroyed the evidence the
user needed to judge how bad it was. Record the reconciled verdict:

```
schematic review e2e-result clean|findings --summary "<one line>" --schematic <name>
```

**Feature done** = every group swept PRISTINE (`#2`) + consistency CLEAN (`#3`) + e2e
tracing dispositioned (`#4`). A clean tracing pass proceeds untouched; only its findings
stop for the user to rule on. `schematic review status` shows the mode, `base_ref`, the
latest sweep's per-batch verdicts, the consistency state, and the e2e state.

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
