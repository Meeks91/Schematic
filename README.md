# Schematic

Multi-phase feature planning skill for Claude Code. Grills the user to produce a feature spec with acceptance criteria, derives class topology, directory structure, contracts with tests, injection DAG, sequence diagram, then generates agent-ready tasks.

## Installation

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/Meeks91/Schematic.git ~/.claude/skills/schematic
```

Or project-level:

```bash
git clone https://github.com/Meeks91/Schematic.git .claude/skills/schematic
```

The `scripts/` directory should be symlinked onto PATH (or added directly):

```bash
ln -s ~/.claude/skills/schematic/scripts/schematic ~/.claude/scripts/schematic
ln -s ~/.claude/skills/schematic/scripts/schematic-task-done ~/.claude/scripts/schematic-task-done
```

## Usage

Invoke with `/schematic` in Claude Code, or when you want to architect a feature end-to-end before implementation.

## Skill Layout

```
schematic/
├── SKILL.md                        ← entry point: cross-cutting rules, structural rules, file format specs
├── standards_resolution.md         ← Phase 0: how standards are resolved/learned per repo
├── phase_1_objective_and_acs.md    ← Phase 1: feature spec + acceptance criteria
├── phase_2_topology.md             ← Phase 2: class/component structure + Class ACs
├── phase_3_directory.md            ← Phase 3: file layout
├── phase_4_contracts_and_tests.md  ← Phase 4: interfaces, models, Function ACs, tests
├── phase_5_injection_dag.md        ← Phase 5: dependency wiring + app integration
├── phase_6_sequence.md             ← Phase 6: runtime flow diagrams (ASCII + Mermaid)
├── phase_7_tasks.md                ← Phase 7: agent-ready task generation
├── phase_8_implementation_loop.md  ← Phase 8: execution (manual or auto mode)
├── audits/                         ← background audit agents dispatched at phase-end
│   ├── README.md                   ← dispatch protocol + output contract
│   ├── _format.md                  ← output schema, severity gates, hard caps
│   ├── _precedence.md              ← DO NOT FLAG list (confirmed non-issues)
│   ├── ac_audit.md                 ← Phase 1 audit
│   ├── topology_audit.md           ← Phase 2 audit
│   ├── contract_audit.md           ← Phase 4 audit
│   ├── sequence_audit.md           ← Phase 6 audit
│   └── end_to_end_audit.md         ← Post-Phase 7 audit
├── scripts/
│   ├── schematic                   ← main CLI (Python) — gates, state, validation
│   ├── schematic-task-done         ← task completion with drift reporting
│   ├── overview.py                 ← schematic overview dashboard launcher
│   ├── track.py                    ← execution trace sub-skill CLI
│   ├── test_schematic.py           ← CLI tests
│   └── test_schematic_task_done.py ← task-done tests
└── reference/
    ├── component_types.md          ← class-suffix vocabulary + banned suffixes
    ├── good_bad_class_ac.md        ← Class AC examples
    ├── good_bad_function_ac.md     ← Function AC examples
    ├── good_bad_test_naming.md     ← test naming examples
    ├── track_subskill.md           ← execution trace sub-skill docs
    ├── headless_review_agent.md    ← review agent prompt template
    ├── agent_responder.py          ← shared Q&A agent (spawns claude -p with context)
    ├── shared_utils.py             ← IDE integration + project root resolution
    ├── mermaid_edit/               ← live-preview Mermaid editor (browser-based)
    │   ├── bridge.py               ← HTTP server + question relay
    │   ├── editor.html             ← editor UI
    │   ├── watcher.py              ← file watcher for hot reload
    │   ├── mermaid.min.js          ← bundled Mermaid renderer
    │   ── qa-bubble-component.js  ← shared Q&A chat bubble component
    └── overview_ui/                ← schematic overview dashboard (browser-based)
        ├── overview.html           ← dashboard UI
        ├── mermaid-editor-component.js
        ├── marked.min.js           ← markdown renderer
        └── purify.min.js           ← HTML sanitiser
```

## Phases

| # | Phase | Output files | Audit |
|---|---|---|---|
| 0 | Standards Resolution | `.claude/standards.json` (repo) | — |
| 1 | Objective & ACs | `objective.md`, `research/*.md` | `ac_audit.md` |
| 2 | Topology | `components/_overview.md` | `topology_audit.md` |
| 3 | Directory Structure | `objective.md` §Directory | — (artifact gate) |
| 4 | Contracts & Tests | `components/<class>.md`, traceability matrix | `contract_audit.md` |
| 5 | Injection DAG | `dag.mmd`, `components/_overview.md` §DAG | — (artifact gate) |
| 6 | Sequence Diagram | `sequence.mmd`, `components/_overview.md` §Sequence | `sequence_audit.md` + artifact gate |
| 7 | Tasks | `tasks.md` | `end_to_end_audit.md` |
| 8 | Implementation | code + `implementation_report.md` | per-task review gate |

**Artifact gates** (Phases 3, 5, 6): `schematic phase complete` rejects the lock if the required files/sections don't exist on disk. Prevents "shown in chat but not written" drift.

## CLI Surface

```
schematic init <name>                                  # scaffold bundle
schematic status [name]                                # progress view
schematic validate [name]                              # AC pyramid + xref integrity

schematic phase audit --schematic <name> <N> <result>  # record audit result
schematic phase sign-off --schematic <name> <N>        # record user sign-off
schematic phase complete --schematic <name> <N>        # lock phase (enforces audit + sign-off + artifacts)

schematic task next [name] [--peek]                    # claim next task (auto in_progress; --peek to inspect only)
schematic task show <tag> --schematic <name>           # flatten task + component context
schematic task status <tag> <status> --schematic <name>  # transition task state
schematic task review-result <tag> <verdict> --schematic <name>  # record review verdict
schematic task complete <tag> --schematic <name>       # mark complete (requires clean review)
schematic task note <tag> "<text>" --schematic <name>  # add agent note

schematic review start [--auto --goal "..."] --schematic <name>  # begin Phase 8
schematic review sweep --schematic <name>              # diff-only style sweep (batch ≤5 files)
schematic review batch-result <id> <verdict> --schematic <name>  # record batch result
schematic review e2e --schematic <name>                # master-agent correctness gate
schematic review e2e-result <verdict> --schematic <name>  # record e2e result
schematic review status --schematic <name>             # current review state

schematic mermaid [--file <path>] [name]               # validate .mmd diagrams

schematic-task-done <tag> --matched [y|n] --updated [y|n]  # completion with drift reporting
```

## Standards Resolution (Phase 0)

Schematic absorbs the standards of the repo it runs in — design, types, styling, and testing conventions are **pluggable per-slot**, and anything unmapped is **learned from the codebase**. Full protocol: `standards_resolution.md`.

**Slots:**

| Slot | Governs |
|---|---|
| `architecture` | service layout, directories, models placement, DI, boundaries |
| `types` | class-suffix / component-type vocabulary |
| `styling.<language>` | naming, formatting, idioms per language |
| `testing` | test planning, naming, structure |
| `exemplars` | known-good directories to imitate |

**Resolution order** (at `schematic init`):

```
repo .claude/standards.json ──exists──► read mapped modules, done
  └─ else ~/.claude/standards.json ───► propose mapping → confirm → copy into repo
       └─ else discover skills with metadata.standards-slot ─► interview
            └─ unresolved slots ──────► LEARN: derive from exemplar code,
                                        write docs/schematics/_standards/learned_<slot>.md,
                                        gate it, point the manifest at it
```

## Output Bundle

Each schematic produces a `docs/schematics/<feature_name>/` directory:

```
docs/schematics/<feature_name>/
├── objective.md              ← what + why (context, ACs, decisions, directory)
├── research/*.md             ← investigation artifacts
├── research/traces/<name>/   ← execution traces
├── components/_overview.md   ← summary table, DAG, sequence, traceability
├── components/<class>.md     ← per-class contract (self-contained)
├── tasks.md                  ← agent-ready work units
├── dag.mmd                   ← Mermaid injection DAG
├── sequence.mmd              ← Mermaid sequence diagram
└── implementation_report.md  ← divergences, deferred items, commit status
```

## Enforcement Gates

| Gate | What it prevents |
|---|---|
| `phase complete` artifact checks | Artifacts shown in chat but not written to disk |
| `task next` auto-claims | Implementation started without kanban state change |
| `phase complete` audit+sign-off | Phase locked without quality gate |
| `task status` legal transitions | Illegal task state jumps |
| `schematic-task-done` review check | Task completed without passing review |
| `schematic validate` | Cross-ref integrity drift (blockers, components, ACs) |

## Visual Tools

**Mermaid Editor** — browser-based live-preview editor with embedded Q&A bubble. Launched by Phase 6 or via `/mermaid-edit`. The Q&A agent receives the diagram content + companion doc (`_overview.md`) + bundle file tree + Feature ACs as context.

```bash
python3 ~/.claude/skills/schematic/reference/mermaid_edit/bridge.py <path-to.mmd>
```

**Overview Dashboard** — renders the full schematic bundle (objective, components, diagrams, tasks) in a single browser view.

```bash
python3 ~/.claude/skills/schematic/scripts/overview.py <schematic-name>
```

## Tests

```bash
python3 -m pytest scripts/test_schematic.py scripts/test_schematic_task_done.py -v
```
