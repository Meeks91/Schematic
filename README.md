# Schematic

Multi-phase feature planning skill for Claude Code. Grills the user to produce a feature spec with acceptance criteria, derives class topology, directory structure, contracts with tests, injection DAG, sequence diagram, then generates agent-ready tasks.

## Installation

Clone this repo into your Claude Code skills directory:

```bash
git clone https://github.com/Meeks91/Schematic.git ~/.claude/skills/schematic
```

Or for project-level installation:

```bash
git clone https://github.com/Meeks91/Schematic.git .claude/skills/schematic
```

## Usage

Invoke with `/schematic` in Claude Code, or when you want to architect a feature end-to-end before implementation.

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

**How it resolves**, at `schematic init`:

```
repo .claude/standards.json ──exists──► read mapped modules, done
  └─ else ~/.claude/standards.json ───► propose mapping → confirm → copy into the repo
       └─ else discover skills carrying `metadata.standards-slot` frontmatter → interview
            └─ unresolved slots ──────► LEARN: derive conventions from exemplar code,
                                        write docs/schematics/_standards/learned_<slot>.md,
                                        gate it, point the manifest at it
```

A manifest entry is `skill:<name>` (a Claude Code skill in `.claude/skills/` or `~/.claude/skills/`), `file:<repo-relative path>`, or `learn`. Every phase then reads and **quotes** the resolved modules — class names (P2), contracts and test naming (P4), task wording (P7), and the Phase 8 review gate all run against them. When no manifest exists anywhere, the legacy behaviour applies: the project's `CLAUDE.md` + `~/.claude/CLAUDE.md` are the standards.

## Phases

0. **Standards Resolution** — resolve or learn the repo's standards modules (see above)
1. **Objective & Acceptance Criteria** — define what the feature does and how to verify it
2. **Topology** — class/component structure
3. **Directory** — file layout
4. **Contracts & Tests** — interfaces and test specifications
5. **Injection DAG** — dependency wiring
6. **Sequence** — runtime flow diagram
7. **Tasks** — agent-ready implementation steps
8. **Implementation Loop** — execute tasks with feedback
