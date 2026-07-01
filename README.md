# Schematic

```text
███████╗ ██████╗██╗  ██╗███████╗███╗   ███╗ █████╗ ████████╗██╗ ██████╗
██╔════╝██╔════╝██║  ██║██╔════╝████╗ ████║██╔══██╗╚══██╔══╝██║██╔════╝
███████╗██║     ███████║█████╗  ██╔████╔██║███████║   ██║   ██║██║
╚════██║██║     ██╔══██║██╔══╝  ██║╚██╔╝██║██╔══██║   ██║   ██║██║
███████║╚██████╗██║  ██║███████╗██║ ╚═╝ ██║██║  ██║   ██║   ██║╚██████╗
╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚═════╝

              t h e   d e s i g n   i s   t h e   c o n t r a c t

   spec ─▶ topology ─▶ contracts ─▶ DAG ─▶ sequence ─▶ tasks ─▶ build ─▶ compress
   └────────────────── audit ▸ sign-off ▸ lock at every gate ───────────────────┘
```

**An agentic development kit** — built for any agentic harness that supports Agent Skills; Claude Code is the reference harness, not a dependency (see [Portability](#portability)). One agent-first pipeline for the arms of development you currently orchestrate separately — planning, implementation, review, standards, knowledge compression. "Build me X" becomes a locked, cross-referenced blueprint; implementation is driven against it through gates a language model cannot talk its way past.

**The design is the contract.** Code that diverges is corrected — or the schematic is amended with sign-off. Nothing lands silently: the mental model you approved during planning is what exists at the end.

## The kit

| Arm | What you get |
|---|---|
| **Plan** | Feature ACs → class topology → per-class contracts + tests → injection DAG → sequence diagram → agent-ready tasks. Boxed cards, dependency grids, interactive diagrams — structure exposes design flaws that prose hides. |
| **Implement** | Task-by-task execution against the blueprint: CLI-driven kanban, sketch gates (manual) or an autonomous driver loop (auto), drift receipts on every completion. |
| **Review** | Continuous automated scrubbing, not one model doing the right thing: phase audits, a diff-scoped review on every task, a batch-until-pristine sweep, a master e2e gate — every verdict recorded in state the agent cannot forge. |
| **Standards** | Modular slots — architecture, component types, styling per language, testing, review. Point them at skills you already like, or **learn** them from your codebase's exemplars. Greenfield (bring your style) and brownfield (absorb the existing one) with the same mechanism. |
| **Compress** | Durable knowledge (sequence, decisions, core summary) merges into your repo's arch docs; the planning bundle retires clean. |

## Why trust it

- **Every decision traces.** Feature AC → Class AC → Function AC → AC Test. A traceability matrix proves the pyramid is complete before a line of code is written.
- **Gates are enforced by a CLI, not by discipline.** Phases can't lock without a recorded audit + sign-off + on-disk artifacts; diagrams can't lock if they don't parse; tasks can't complete without a clean review verdict.
- **Audits are background agents with a muzzle.** Strict output schema, severity gates, a do-not-flag list — signal, not a 20-bullet wall. Reviewers see only diff hunks, so false flags on pre-existing code are structurally impossible.
- **A team artifact, not a scrollback.** The bundle is plain markdown + Mermaid in the repo — teammates read `objective.md` in two minutes, review contracts in the PR, open the same dashboard locally, and sign off on a durable artifact.
- **A loop within a loop.** Run long builds under a goal runner: the outer loop guarantees the agent doesn't give up; Schematic's inner gates guarantee every iteration does *verified* work. State lives on disk — re-entry is `schematic status` → next unblocked task, never memory.

![Schematic overview dashboard — one browser view over the whole bundle: objective, component contracts, diagrams, research, and execution state](docs/assets/dashboard.png)

![Live Mermaid editor — source and rendered sequence diagram side by side, with the Q&A input routing questions to the session agent](docs/assets/editable-diagram-with-chat.png)

![Interactive diagram view in the dashboard — rendered sequence flow with AC-labelled frames](docs/assets/interactive-diagram.png)

## Install

```bash
git clone https://github.com/Meeks91/Schematic.git ~/.claude/skills/schematic
```

Or project-level:

```bash
git clone https://github.com/Meeks91/Schematic.git .claude/skills/schematic
```

Symlink the CLI onto PATH:

```bash
ln -s ~/.claude/skills/schematic/scripts/schematic ~/.claude/scripts/schematic
ln -s ~/.claude/skills/schematic/scripts/schematic-task-done ~/.claude/scripts/schematic-task-done
```

Zero runtime dependencies — the CLI, the audit protocol, the dashboard, and the Mermaid editor are stdlib Python + vanilla JS.

## Usage

Invoke `/schematic` in Claude Code, or ask to architect a feature end-to-end before implementation. `schematic init <feature>` scaffolds the bundle and reports your standards coverage slot by slot.

## The pipeline

| # | Phase | Output | Gate |
|---|---|---|---|
| 0 | Standards Resolution | `.claude/standards.json` | interview / learn-from-codebase |
| 1 | Objective & Feature ACs | `objective.md`, `research/*.md` | audit + sign-off |
| 2 | Topology (Class ACs) | `components/_overview.md` | audit + sign-off |
| 3 | Directory Structure | `objective.md` §Directory | artifact check |
| 4 | Contracts, Models, Tests | `components/<class>.md`, traceability matrix | audit + sign-off |
| 5 | Injection DAG | `dag.mmd`, §DAG + §Integration | artifact check + **mermaid validation** |
| 6 | Sequence Diagram | `sequence.mmd`, §Sequence | audit + artifact check + **mermaid validation** |
| 7 | Tasks | `tasks.md` | end-to-end audit + sign-off |
| 8 | Implementation | code + `implementation_report.md` | per-task review verdicts + pristine sweep + e2e gate |
| 9 | Compression | knowledge merged into repo arch docs | lock, then cleanup |

Phase 8 runs **manual** (sketch → confirm → implement, per task) or **auto** (user-opted autonomous loop with per-task diff reviews, a batch-until-pristine style sweep, and a master-agent correctness gate). Re-sweeps are incremental: files unchanged since their last clean review are skipped, not re-reviewed.

**Phase 1 — the objective**, human-readable in two minutes, and **Phase 3 — the feature's footprint**, every file annotated with the AC that necessitated it:

<p>
  <img src="docs/assets/objective.png" width="49%" alt="objective.md — context, purpose, functional ACs with What/Why per sub-change" />
  <img src="docs/assets/directory-structure.png" width="49%" alt="Directory structure — NEW/MODIFIED annotations with driving AC refs" />
</p>

**Phase 4 — per-class contracts**: signatures, models, behaviour notes, and the feature/branch tests that prove them, one self-contained card per class:

<p>
  <img src="docs/assets/contract.png" width="49%" alt="Contract card — constructor deps, method signatures, behaviour" />
  <img src="docs/assets/component-spec.png" width="49%" alt="Component spec — models, errors, feature and branch tests" />
</p>

**Phase 8 — execution**: tasks flow across a kanban driven entirely by the CLI's legal state transitions; review findings land as notes on the task:

<p>
  <img src="docs/assets/agent-kanban.png" width="49%" alt="Task kanban — Not Started / In Progress / Review / Done, dependency tags per card" />
  <img src="docs/assets/agent-task-with-notes.png" width="49%" alt="Task detail — agent notes and review findings attached to the task" />
</p>

## Enforcement gates

| Gate | What it prevents |
|---|---|
| `phase complete` artifact checks | Artifacts shown in chat but never written to disk |
| `phase complete` mermaid checks (P5/P6) | Locking a DAG or sequence diagram that doesn't parse |
| `phase complete` audit + sign-off | Locking a phase without its quality gate |
| `task next` auto-claim | Implementation starting without a kanban state change |
| `task status` legal transitions | Illegal task state jumps |
| `task complete` / `schematic-task-done` review check | Completing a task that never passed review |
| `schematic-task-done --matched/--updated` | Silent schematic drift — divergence is recorded, always |
| `schematic validate` | Cross-reference rot (blockers, component files, AC pyramid) |
| Incremental sweeps | Token burn from re-reviewing already-clean files |

## CLI

`schematic --help` is the surface of record. Command groups:

```
schematic init|status|validate|mermaid            bundle lifecycle + integrity
schematic phase audit|sign-off|complete           gate state, phases 1-9 (audit: 1,2,4,6,7)
schematic task next|show|status|note|review-result|complete    task loop
schematic review start|sweep|batch-result|e2e|e2e-result|status  phase 8 review
schematic questions / schematic answer            dashboard Q&A relay
schematic overview                                browser dashboard
schematic track init|validate|show                execution traces
schematic-task-done <tag> --matched y|n --updated y|n   completion + drift report
```

## Standards manifest (Phase 0)

Schematic absorbs the conventions of the repo it runs in. Each **slot** maps to a module; anything unmapped is **learned** from your codebase's exemplar directories and written back as a reviewed module.

| Slot | Governs | Consumed by |
|---|---|---|
| `architecture` | service layout, directories, DI, boundaries | P2, P3, P5 |
| `types` | class-suffix vocabulary, banned suffixes | P2 + audits |
| `styling.<language>` | naming, idioms, defensive-code policy | P4, P8 (inlined into sweep prompts) |
| `testing` | test planning, naming, assertion style | P4, P7, P8 (inlined into sweep prompts) |
| `review` | review lenses, gate criteria | audits + P8 review prompts |
| `exemplars` | known-good directories to imitate | learn mode, P8 |
| `schematic.reviewModel` | model for review subagents (default `sonnet`) | P8 |
| `schematic.completionCompression` | what survives into repo docs after Phase 9 | P9 |

Resolution order: repo `.claude/standards.json` → global `~/.claude/standards.json` (confirmed + copied in) → discover skills by frontmatter → interview → **learn from the codebase**. `schematic init` prints slot-by-slot coverage so gaps are visible on day one.

## Visual tools

**Overview dashboard** — `schematic overview` renders the full bundle (objective, components, DAG, sequence, tasks, traces) in one browser view.

**Live Mermaid editor** — round-trips any `.mmd` on disk with live preview, zoom/pan, notes, and per-node IDE jump. Ctrl+S saves; **Save & Close** ends the session and hands the file back to the agent. Handles very large diagrams. *(Pictured at the top.)*

**Q&A relay** — both UIs embed a chat bubble. Questions asked there are compiled into fully-contextualised prompts (diagram + bundle tree + Feature ACs + thread) and queued for the main session agent:

```
schematic questions                    # list unanswered, with full context
schematic answer overview#0 "<text>"   # reply — the bubble updates live
```

## Portability

Schematic ships in the Agent Skills format, so it runs on any harness that supports skills. What a harness needs to provide: load `SKILL.md` as instructions, execute shell commands (the CLI), read/write files, and dispatch subagent prompts (audits + reviews). The machinery underneath is runtime-agnostic by design — nothing shells out to `claude` or any vendor binary:

| Piece | Coupling |
|---|---|
| CLI (gates, state, kanban, validate) | Plain stdlib Python — any agent or human runs it |
| Bundle (`objective.md`, contracts, `.mmd`) | Markdown + Mermaid — any model reads and writes it |
| **Review loop** | The CLI is the gatekeeper, the session agent is the dispatcher: prompts are *printed*, verdicts are *recorded* (`task review-result`, `review batch-result`). Sweep prompts inline the diff hunks + standards content so the reviewer needs **zero file access** — any subagent, any model, any harness |
| Audits | Same pattern — self-contained prompt files, results recorded via `phase audit` |
| Dashboard + Mermaid editor | Stdlib HTTP servers + vanilla JS in a browser; Q&A relays through JSON files (`schematic questions` / `answer`) |
| Skill packaging (`SKILL.md`, phase files) | Standard Agent Skills format — loads in any skills-aware harness; even without one, they're plain instruction files any agent can follow |

Practically: another runtime (or a plain human) drives the same pipeline by running the CLI, dispatching the printed prompts to whatever model it has, and recording the verdicts. The gates neither know nor care who's on the other end.

## Output bundle

```
docs/schematics/<feature>/
├── objective.md              what + why: context, ACs, decisions, directory
├── research/*.md             investigation artifacts
├── research/traces/<name>/   execution traces through existing code
├── components/_overview.md   component summary, DAG, sequence, traceability
├── components/<class>.md     per-class contract — self-contained
├── tasks.md                  agent-ready work units
├── dag.mmd · sequence.mmd    Mermaid diagrams (validated at lock)
└── implementation_report.md  divergences, deferred items, commit status
```

After Phase 9, the durable knowledge (sequence, core summary, decision log) is compressed into your repo's architecture docs and the bundle is retired.

## Skill layout

```
schematic/
├── SKILL.md                        entry point: cross-cutting rules, gates, formats
├── standards_resolution.md         Phase 0: slot mapping + learn mode
├── phase_1..9_*.md                 per-phase binding rules
├── audits/                         background audit prompts + output schema
├── scripts/                        CLI, dashboard server, trace tool, tests
└── reference/                      component-type taxonomy, examples,
                                    mermaid editor, overview UI, Q&A responder
```

## Tests

```bash
python3 -m pytest scripts/test_schematic.py scripts/test_schematic_task_done.py -v
```
