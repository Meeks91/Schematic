# End-to-End Audit (Post-Phase 7 — Full Schematic Consistency)

Final quality gate before Phase 8. Walk the whole bundle for broken cross-references and for every gap a builder would hit: a type its card cannot reach, a task ordered before the card that owns its types, a value nobody ruled. Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/objective.md` (Phase 1 + directory structure)
- `<schematic_dir>/components/_overview.md` (Component Summary, AC coverage tally, DAG, sequence)
- `<schematic_dir>/components/*.md` (every class contract)
- `<schematic_dir>/dag.mmd`
- `<schematic_dir>/tasks.md`

## Checks (in order)

### 1. AC traceability pyramid
- Run `schematic validate <name>` — it fails on any Feature AC no card test cites and any card whose tests cite no Feature AC.
- Every Feature AC has ≥1 Class AC; every Class AC ≥1 Function AC; every Function AC ≥1 test. Flag orphans at any level.

### 2. Topology and DAG
- Every class in `components/_overview.md` §Component Summary has a card and appears in `dag.mmd` (modulo FE/BE split); every card is in the Summary.
- Every `dag.mmd` edge matches a constructor dependency on a card; the graph is acyclic.

### 3. Builder gaps (mechanical first)
- Run `schematic package check --all --schematic <name>`. Every `OWNED-BY-<tag>` line is a BLOCKER: the task uses a type owned by a task it does not wait on — add `Blocked by: <tag>` or move the type onto the card that needs it first. Every `MISSING` line is a BLOCKER.
- Any wire shape, cap, code, enum spelling or prompt rendering a task's card still leaves open is a BLOCKER — rule it before lock.
- Every task carries `Model: opus | sonnet` per `phase_7_tasks.md`.

### 4. Tasks integrity
- Every class in the Component Summary has a task (excluding FE classes covered by FE tasks).
- Every task's Feature AC references match `objective.md` §1.

### 5. Stale references
- Class names renamed during the design, still present anywhere — flag.
- "TODO", "TBD", "(pending)" in any locked artifact — flag for resolution.

### 6. Banned terminology (conditional)
Only if the project's CLAUDE.md, the resolved standards modules, or the Decision Log ban specific terms: search every locked artifact for them. No list → skip; never invent one.

### 7. Deferred items are explicit
Any Feature AC marked DEFERRED has a corresponding 501-return note in the contract. Flag silent deferrals.

### 8. Triggered lenses (conditional — driven by the resolved review modules)

A lens in the resolved `review` modules (every module the manifest `review` slot maps, in order) may declare its scope with a `Triggers:` line of path globs under its heading. A lens with no `Triggers:` line is unconditional and was already applied by the standards pass — skip it here. For each triggered lens:

1. Match every path a task in `tasks.md` creates or modifies against its globs. Nothing matches → skip it, saying so in one line.
2. Anything matches → run the lens's **planning checks** (the subsection it marks for this audit) against the matching tasks AND the real files they name. Read the files; the task text is not the evidence.
3. Report under the lens's own heading, applying its FAIL conditions verbatim; a lens FAIL blocks the phase lock like any check here.

Tasks are the trigger surface at planning time; the diff is at review time (the Phase 8 sweep). An artifact a triggered lens requires (a runbook, a sequencing table, an ordered plan) becomes part of the phase: every task that triggered the lens links it, or that is a finding. A prose assurance is never a mechanism: if the rule is "this must not run yet", the file must sit where the runner cannot reach it.

### 9. Count tally
Feature ACs N (X deferred) · Classes N (BE X, FE Y) · Function ACs ~N · AC tests ~N · Branch tests ~N · Tasks N (opus X, sonnet Y)

## Output

Return findings strictly in the format from `audits/_format.md`.

If clean, return:
```
✓ Clean

Counts: <tally>
```
