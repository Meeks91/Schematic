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

## Phases

1. **Objective & Acceptance Criteria** — define what the feature does and how to verify it
2. **Topology** — class/component structure
3. **Directory** — file layout
4. **Contracts & Tests** — interfaces and test specifications
5. **Injection DAG** — dependency wiring
6. **Sequence** — runtime flow diagram
7. **Tasks** — agent-ready implementation steps
8. **Implementation Loop** — execute tasks with feedback
