---
name: schematic
description: Multi-phase feature planning skill. Grills the user to produce a feature spec with ACs, derives class topology, directory structure, contracts with tests, injection DAG, sequence diagram, then generates agent-ready tasks. Invoke when user wants to architect a feature end-to-end before implementation, or mentions "schematic".
---

# Schematic — Feature Planning Skill

> [!CAUTION]
> ## On entry: run `schematic --help` to discover the CLI surface. NON-NEGOTIABLE.
>
> This skill bundles its CLI at `scripts/schematic` (symlinked onto PATH at `~/.claude/scripts/schematic`, so bare `schematic …` resolves) that tracks gate
> state, audit results, sign-offs, and phase completion for **every phase 1–9**
> — not just Phase 8. Working without it leaves state untracked and `validate`
> blind.
>
> `--help` is the surface of record. Command groups:
>
> ```
> schematic init|status|validate|mermaid          # bundle lifecycle + integrity
> schematic phase audit|sign-off|complete         # gate state per phase 1-9 (audit: 1,2,4,6,7 only)
> schematic task next|show|status|note|review-result|complete   # phase 8 task loop
> schematic review start|sweep|batch-result|e2e|e2e-result|status  # phase 8 review
> schematic questions / schematic answer          # dashboard/editor Q&A relay
> schematic overview / schematic track            # dashboard + execution traces
> ```
>
> **Edit any `.mmd` visually (on request, any phase):** launch the bundled live-preview editor — `python3 <skill_dir>/reference/mermaid_edit/bridge.py <path-to.mmd>` (backgrounded; blocks until the user clicks Save & Close, then re-read the file — Ctrl+S in the editor saves without closing). Handles very large diagrams. See `phase_6_sequence.md` → "Visual round-trip editor".
>
> **Dashboard/editor questions reach YOU:** questions the user asks in any browser UI queue for this session. After a UI session (or when the user says they asked something there), run `schematic questions` and reply with `schematic answer <id> "<text>"` — the bubble updates live. Never leave the queue undrained.
>
> **Binding workflow per gate:** dispatch audit → record audit result via CLI
> → present to user → on `y` reply, record sign-off via CLI → lock with
> `phase complete`. Never accept text "y" as the only proof of sign-off — the
> CLI is the state of record.

> [!NOTE]
> ## On entry: notify the user (once per session).
>
> 1. **Standards config check:** if `.claude/standards.json` does NOT exist at the repo root, tell the user: _"No standards manifest found. Run `schematic init` to configure your project's coding conventions (component types, styling, testing). The skill uses your resolved standards to shape every phase."_ Offer to onboard them: map slots to skills they already have, or LEARN unmapped slots from their codebase's exemplar directories (`standards_resolution.md` → Learn mode).
> 2. **Visual tools available:** _"You can request `schematic overview` to launch the interactive dashboard (objective, components, DAG + sequence diagrams, tasks in one view), or the bundled live Mermaid editor to hand-edit any diagram. Both have a Q&A bubble that routes questions to me."_
>
> **Re-surface, don't bury:** the dashboard and editor are offered again at the phases where they matter most — Phase 5 (DAG) and Phase 6 (sequence) gates explicitly present them (see those phase files). A user who never learns the screens exist is a skill bug.

> [!CAUTION]
> ## RESOLVED STANDARDS are the GROUND TRUTH for code style. NON-NEGOTIABLE.
>
> Before any phase, proposal, directory tree, class name, file path, or "where should X live?" question:
>
> 1. **RESOLVE** the standards manifest — repo `.claude/standards.json`, else `~/.claude/standards.json`, else the Phase 0 discovery/learn flow. Full protocol: `standards_resolution.md` (run at `schematic init`). Legacy fallback when no manifest exists: the project's `CLAUDE.md` (root + nested) + the user's `~/.claude/CLAUDE.md` ARE the standards.
> 2. **READ** every resolved module the phase consumes (architecture / types / styling.<language> / testing — consumption table in `standards_resolution.md`), plus the project's `CLAUDE.md` (always — it overrides modules on conflict).
> 3. **APPLY** the conventions verbatim — naming, suffix vocabulary, file layout, model placement, service organisation, class size, comment policy, test conventions, cascading style.
> 4. **QUOTE** the rule you are applying — and its source module — when you present the result (`python-standards: "NEVER default parameters"`). Cite it; do not paraphrase, do not "interpret".
>
> **These conventions OVERRIDE the schematic's own templates and examples when they conflict.** The skill shows you HOW to plan; the resolved standards tell you WHAT shape the plan must take.
>
> **Forbidden:** drawing a tree, naming a class, choosing a suffix, or asking "where should X go?" before resolution has run. The answer is in the resolved modules — quote the rule that applies.
>
> Applies to **every phase** — class names (P2), method signatures (P4), test naming (P4), task wording (P7).

## Purpose of this skill (binding — re-read at every phase boundary)

**The skill exists to constantly surface context to the user so they remain present in *what* we are planning and *why*.**

Every artifact carries its own reason for existing:

- Every proposed class, every contract, every task **shows its driving AC** alongside the change — **never a bare tag, always with a one-line title** (`1.A — Generator-then-judge LLM pipeline produces ranked derivation suggestions`). No human can remember which tag is which.
- Every gated message **opens with the Frame Header** (schematic, phase, locked-so-far, this-gate, driving ACs) — exact template under **Structural Rules → Frame Header**. Defined once; never restated per phase.
- Every gate **leads with the question + the why** (`Question: <one sentence>` / `Why: <what's blocked or at stake>`).
- Every box, card, and diagram **back-references** the prior phase that motivated it (Phase 4 contract cards link to the §3.N topology summary that justified the class).
- **Visual-first.** ASCII boxes, tables, diagrams over prose paragraphs. Prose hides drift; structure exposes it.

If you find yourself writing a proposal without naming the AC it implements, STOP. The user has lost context — re-anchor before continuing.

---

## What This Produces

The output of this skill is a **multi-file engineering blueprint** — a design schematic bundled under `docs/schematics/<feature_name>/`. Assembled **progressively as gates confirm**. The user can open the directory mid-session to review the locked state at any time.

**Bundle directory layout:**
```
docs/schematics/<feature_name>/
├── objective.md                    ← human frame (context, objective, purpose, core summary, functional ACs, key findings, decision log, directory)
├── research/
│   ├── <investigation>.md          ← analysis artifacts (field mappings, comparisons, gap analysis)
│   └── traces/
│       ├── <trace-name>/           ← per-flow execution trace (trace.json, trace.mmd, trace.paths.json, trace.md)
│       └── _index.json             ← registry of all traces
├── components/
│   ├── _overview.md                ← cross-cutting: DAG edge inventory, sequence (ASCII), traceability matrix, app integration
│   ├── effects_linker.md           ← self-contained: Class AC, contract, models, Function ACs, AC tests, branch tests
│   ├── conviction_resolver.md
│   └── ...
├── tasks.md                        ← agent-ready work units, one task per class
├── dag.mmd                         ← Mermaid injection DAG
├── sequence.mmd                    ← Mermaid sequence diagram
├── implementation_report.md        ← Phase 8 completion record: gates, review ledger, post-lock amendments, deferred items
└── [DELETED after Phase 9 — knowledge compressed into repo arch docs]
```

**File responsibilities:**

| File | Purpose | Audience |
|---|---|---|
| `objective.md` | Context, objective, purpose, core summary, functional ACs, key findings, decision log, directory structure | Human — "what and why" in 2 minutes |
| `research/<name>.md` | Investigation artifacts — field mappings, schema comparisons, gap analysis | Human — "what we learned" |
| `research/traces/<name>/` | End-to-end flow trace through existing code (see `track_subskill.md`) | Human + Agent — "how the existing system works" |
| `components/<class>.md` | Full contract per class — self-contained, no cross-file dependency needed | Human + Agent — "how, exactly" |
| `components/_overview.md` | Component summary table + cross-cutting views: DAG text, sequence ASCII, traceability matrix, integration | Human + Agent — "how it all wires together" |
| `tasks.md` | One task per class, references component files by name | Agent — "do this" |
| `dag.mmd` | Mermaid injection DAG (authoritative when >8 nodes) | Visual tool rendering |
| `sequence.mmd` | Mermaid sequence diagram | Visual tool rendering |
| `implementation_report.md` | Phase 8 completion record — MINIMAL: signed-off divergences, deferred decisions, commit status; success elsewhere assumed; reviews one line | Human — "what diverged and what's outstanding" |

**Write routing by phase:**

| Phase | Writes to |
|---|---|
| 1: Context, Objective, Purpose, Core Summary, Functional ACs | `objective.md` + `research/*.md` (investigations) |
| 1: Key Findings (from research/session) + Decision Log | `objective.md` |
| 1: Traces (optional, on request) | `research/traces/<name>/` |
| 2: Topology (class summary + Class ACs) | `components/_overview.md` (summary table) |
| 3: Directory structure | `objective.md` |
| 4: Contracts, models, Function ACs, tests | `components/<class>.md` (one per class) |
| 4 end: Traceability matrix | `components/_overview.md` |
| 5: DAG + App Integration | `dag.mmd` + `components/_overview.md` |
| 6: Sequence diagram | `sequence.mmd` + `components/_overview.md` (ASCII) |
| 7: Tasks | `tasks.md` |
| 8: Implementation loop | `implementation_report.md` (created at phase start, updated as gates/reviews/amendments land; link it from the top of `objective.md` so it is reachable from the dashboard) |
| 9: Compression | Writes to `<archDocsPath>/<feature>.md` + sequence; deletes schematic dir per config |

---

## AC Hierarchy (binding mental model)

Every design decision traces through this pyramid. Each layer proves the one above:

```
Feature AC   (Phase 1 — grill)      → "what must the feature achieve?"
  └── Class AC    (Phase 2 — topology)  → "what does this class OWN?"
       └── Function AC (Phase 4 — contracts) → "what must this method achieve?"
            └── AC Test   (Phase 4 — tests)     → "proof that the method delivers"
```

The traceability check at end of Phase 4 validates this pyramid is complete — every Feature AC is covered by Class ACs, every Class AC by Function ACs, every Function AC by an AC Test. Nothing orphaned, nothing assumed.

---

## Execution Order (sequential — no skipping, no reordering)

> [!CAUTION]
> ## ENTERING A PHASE = READING ITS FILES. NON-NEGOTIABLE.
>
> The instant you enter Phase N — before any proposal, any question to the user, any write to disk, any draft of a class, contract, DAG node, or task:
>
> 1. **READ** the phase file (`phase_N_*.md`) in full.
> 2. **READ** every `reference/` file the phase file links to.
> 3. **READ** the corresponding `audits/` prompt if the phase has an audit hook (Phases 1, 2, 4, 6, post-7).
>
> Phase files carry the **phase-specific** binding rules. SKILL.md's cross-cutting rules (Frame Header, visual-first, iteration caps, change-presentation, naming) are **always in context and always apply on top** — a phase file not restating them does not relax them. Working from memory of a prior session — or from this skill's overview alone — is **forbidden**: phase files evolve, and stale recall is the #1 cause of off-spec output.
>
> **Forbidden:**
> - Drafting any Phase N output without having opened `phase_N_*.md` in the current session.
> - Asking the user a Phase N question that the phase file already answers.
> - Citing a rule from memory when the phase file is the source.
>
> **If you find yourself producing Phase N output and cannot point to the line in `phase_N_*.md` you're applying, STOP. Read the file. Then continue.**

| Phase | File to Read at phase start |
|---|---|
| 0: Standards Resolution (at `schematic init`) | `standards_resolution.md` |
| 1: Feature Spec + Feature ACs | `phase_1_objective_and_acs.md` |
| 2: Topology (class responsibilities = Class ACs) | `phase_2_topology.md` |
| 3: Directory Structure | `phase_3_directory.md` |
| 4: Contracts + Models + Function ACs + Tests + Traceability | `phase_4_contracts_and_tests.md` |
| 5: Injection DAG + App Integration | `phase_5_injection_dag.md` |
| 6: Sequence Diagram | `phase_6_sequence.md` |
| 7: Tasks | `phase_7_tasks.md` |
| 8: Implementation Loop (per-task sketch + CLI completion gate) | `phase_8_implementation_loop.md` |
| 9: Compression (integrate knowledge into repo docs) | `phase_9_compression.md` |

---

## Audit Hooks (cross-cutting — applies at phase completion only)

Mandatory background-audit agents run **once per phase, at phase completion** (the final sub-gate that closes the phase) for Phases 1, 2, 4, 6, and post-Phase 7. They catch violations of CLAUDE.md and the schematic rules BEFORE the user locks the phase — when one comprehensive pass over the full phase output is cheaper to act on than a per-sub-gate stream.

**Why phase-completion only (not per-sub-gate):**
- Per-sub-gate auditing re-litigates the same false positives across every batch of 3 classes (e.g. missing `self`, missing `*,`, "emits then raises" mis-flags) — noise without signal.
- One end-of-phase audit reviews the locked phase as a coherent whole, catches inter-class consistency issues a per-gate audit cannot see, and is the natural point to act on findings before moving to the next phase.
- Sub-gate `Confirm: y/comment` sigils still gate user sign-off on each batch of ≤3 items — that's content iteration, not quality gating.

- **Protocol + dispatch format:** see `audits/README.md`.
- **Per-phase audit prompts:** `audits/ac_audit.md`, `audits/topology_audit.md`, `audits/contract_audit.md`, `audits/sequence_audit.md`, `audits/end_to_end_audit.md`.
- **Binding rule:** ONLY the final `Confirm: y/comment` sigil of a phase (the one that closes the phase) MUST be preceded by an audit dispatch + result. Earlier sub-gate sigils within the same phase do NOT require an audit. The audit runs in parallel (background) so wall-clock cost is usually zero, but **never lock the phase without the audit having returned**.
- **Record the audit result via the CLI** before the phase-closing `Confirm: y/comment` sigil:
  ```
  schematic phase audit --schematic <name> <N> "clean"
  schematic phase audit --schematic <name> <N> "<one-line findings summary>"
  ```
  This persists the gate state so `schematic validate` and `schematic status` are accurate.

Why this exists: across sessions, banned suffixes, mis-classified Services, orphan classes, and Phase-N-leakage all got past the planner-agent and were caught 3+ phases later by the user. Audit hooks are the structural fix.

---

## Reference index

Detailed examples and taxonomies that the phase files link to:

| File | Used in |
|---|---|
| `reference/component_types.md` | Phase 2 — class type vocabulary, banned suffixes, stacked-suffix anti-pattern, design smells |
| `reference/good_bad_class_ac.md` | Phase 2 — `UserRepository` good vs bad reference |
| `reference/good_bad_function_ac.md` | Phase 4 — Function AC examples (swallowed empty + clean propagation) |
| `reference/good_bad_test_naming.md` | Phase 4 — test naming pattern + Python test layout pointer |

---

## Structural Rules

**Compression rule (mandatory, binding):**
The schematic is **one rational view** of the design — every fact in exactly one file/section. Cross-reference by filename (`see components/effects_linker.md`), never restate. Tables for structural data (file trees, comparisons); block format when content would collapse to one cell (contract details).

**Frame Header (mandatory — open every gated message with this):**

Defined once here; inherited by every phase — 4 content lines, re-emitted each gate:

```
── SCHEMATIC <name> · PHASE <N>/9 — <title> ──────────────────
Objective:   <one-line session deliverable>
Locked:      P1 ✓  P2 ✓  …        This gate: <what this artifact adds>
Driving ACs: 1.A — <title>, 2.C — <title>
──────────────────────────────────────────────────────────────
```

AC tags MUST carry their one-line title here — no bare refs. Abbreviate with `…` if >2 ACs.

`Locked:` is printed verbatim by `schematic status` (the `locked:` line) — paste it, don't hand-maintain it. Phase files never restate this template; they inherit it.

**Approval gate (mandatory, binding):**

NEVER move past a phase or section without explicit content approval.

A `y` on "Proceed to Phase N?" starts the work. It does NOT approve the output. After the work is done, you MUST still ask for content approval and wait.

Approval requires the literal sigil at the end of your message:

```
Confirm: y/comment
```

You may write to disk freely during the phase — writing is not the gate. **The gate is moving forward.** Before moving to the next phase, the most recent message you sent MUST have ended with `Confirm: y/comment` AND you MUST have received a `y` in reply that referenced that sigil.

If you wrote artifacts and need approval, list them with paths so the user can review on disk before answering:

```
Written this phase:
  - <path>  — <one-line description>
  - <path>  — <one-line description>
Confirm: y/comment
```

**On the user's `y` reply, immediately record both sign-off and completion via the CLI before starting the next phase:**

```
schematic phase sign-off --schematic <name> <N>
schematic phase complete --schematic <name> <N>
```

`phase complete` enforces that an audit result + sign-off are both already recorded. If it errors, you've skipped a step — fix the missing record, do not `--override`. Without this two-line discipline `schematic status` and `schematic validate` are stale and downstream phases have no integrity check to lean on.

**Iteration rule (binding, ZERO exceptions, ALL gated outputs):**

> ⚠️ **MAX 120 LINES OR 3 ITEMS PER GATE — WHICHEVER IS LESS.**
>
> The chat presentation per gate is bounded by **two simultaneous caps**:
>
> 1. **≤120 lines of message body** (rendered output, including code fences but excluding the `Confirm:` sigil).
> 2. **≤3 top-level items** (feature changes / classes / tasks).
>
> **The smaller cap wins.** If 3 classes blow past 120 lines, present fewer — one or two — and split. If 3 items fit in 60 lines, that's fine, present them.
>
> Applies to **every** list the user is asked to confirm:
> - Phase 1b Functional ACs entries
> - Phase 2 topology blocks (classes)
> - Phase 4 contract blocks (classes)
> - Phase 7 **task graph** overview (the grouped dependency tables — gated once). The detailed task blocks beneath it are NOT gated: they are auto-written in one pass because every AC/contract/test they cite was already locked in Phases 1–6 (see `phase_7_tasks.md`).
> - Any other gated list
>
> **Disk is separate.** The 120-line cap is for the chat message; files on disk (`objective.md`, `components/<class>.md`) are as long as needed. For **contract cards**, the chat render IS the full card, identical to disk — fit the cap by presenting fewer cards (down to one, split across gates), NEVER by shrinking into a summary / signature-list / prose variant. Reducing item count is the only lever; card fidelity is fixed. For **large non-card artifacts** (DAGs, sequence diagrams, `objective.md` prose), summarise + link to the file rather than dumping it.

Why: 3 items = a frame the user can hold; 120 lines = one reviewable screen. Sub-items (1.A, 1.B, 1.C) count toward their parent — but if a single parent has >5 sub-items, split it.

**Self-check before sending any gated message:**
0. Opens with the Frame Header? → if not, add it.
1. Count top-level items → if >3, STOP and split.
2. Count rendered lines → if >120, STOP and present FEWER full cards (down to one); never shrink a card into a summary.

Iteration protocol:
1. Present the first ≤3 items with `Confirm: y/comment`.
2. On comment: revise the relevant items and re-present the same ≤3.
3. On `y`: lock them, write to disk, present the next ≤3.
4. Repeat until the full list is locked.
5. After all items are locked, **summarise the full locked list once** so the user sees the whole frame before moving to the next phase.

**Question format (MANDATORY when asking the user a question):**
- Every question must lead with lean-but-sufficient context so the user can answer without scrolling back.
- Structure:
  ```
  Question: <the actual question, one sentence>
  Why:      <the reason we need to decide this — what's blocked or at stake>
  ```

**Communication style (binding throughout this skill):**

Primary mode is visual. Default to structured visuals over prose. In order of preference:

1. ASCII diagrams — call chains, data flow, sequence, state machines, injection DAGs
2. Tables — comparisons, branch matrices, file maps
3. Bullet points — lists, decisions, steps
4. Flow charts / Mermaid — architecture, pipelines, complex wiring
5. Prose — only when none of the above fits

Goal: maximum information density with minimum reading effort. Concise and pointed — don't omit, don't pad. Prose paragraphs are banned outside fenced reference examples — they hide structural problems that bullets and diagrams expose. A poorly wired injection DAG is invisible in prose; it jumps out in a diagram.

**Change-presentation rule (mandatory, binding — use whenever showing edits across files):**

Present every file-by-file change set using `diff` fenced code blocks. Most renderers colour `+` lines green and `-` lines red — this gives the user actual visual differentiation that plain code blocks lack.

Structure:

````
## File N — <path>

```diff
- <removed line>
+ <added line>
```

```diff
  <context line>
- <removed block>
+ <added block>
```
````

- One section per file, with the path as the heading.
- Multiple diff blocks per file for distinct edit groups (imports, signature changes, body changes). Keeps each block small and reviewable.
- Use `! `-prefixed lines inside a diff block to mark **out-of-scope / deferred** callouts — most renderers dim these, giving them visual weight without claiming they're real code changes.
- Use unprefixed context lines (`  <line>`) to anchor edits when the surrounding code matters to the reviewer.

Reserve plain ` ```python ` fences for **new** files only (nothing to diff). Use `diff` blocks for all change presentations across the skill.

**Cross-reference naming rule (mandatory, binding):**

Every task reference uses the canonical three-column form:

```
<tag> | <Action> | <Target>
```

- **tag** — short stable ID for agent-internal cross-referencing (`b.1`, `c.3`). Format is `<group-letter>.<index>` — the CLI parser accepts nothing else. Letters group related work; numbers order within the group. Codes carry no meaning on their own. (`4.A`-style codes are AC stamps, never task tags — see Stamp form below.)
- **Action** — verb in past-participle-imperative form. One of: `Create`, `Modify`, `Rename`, `Tighten`, `Delete`, `Wire`, `Add`, `Split`. The verb tells the reader what the task DOES at a glance.
- **Target** — fully-qualified class, method, or scope. Class names, file paths, or `ClassName.method` are all valid. The reader sees what the task touches.

**Valid:**

```
## b.1 | Create | ReelEnrichmentService.enrich_reels
## c.3 | Tighten | ReelEnrichmentInputsResolver
## a.2 | Add     | EnrichedReelRepository.get_precomputed_enriched_reels
## d.1 | Delete  | LLMReelEnricher

Blocked by: a.1 | Create | Foundations, c.3 | Tighten | ReelEnrichmentInputsResolver
```

**Invalid (bare tags — forbidden):**

```
T-F uses → ReelAnalyserRequest        ← no action, no target
Next: b.1                              ← bare tag
Blocked by: a.1, c.3                   ← bare tags
## T-B: EnrichedReelRepository…        ← old paired form, action missing
```

**Applies to:** task headings in `tasks.md`, conversational references, dependency lists, blocked-by chains, change-log entries, anywhere a task is mentioned. The tag is allowed to appear once on its own line at the top of a section it labels, provided the same line continues with `| Action | Target`. Bare tags anywhere else are forbidden.

**Stamp form for non-task codes** (Feature ACs, Class ACs): still use the `<code> — <description>` pair, since those don't have an Action component:

```
Necessitated by: 4.A — selector picks top-K reels for an enrichment run
```

---

## Schematic File Structure (BINDING)

### objective.md

The clean human-facing doc — a reader understands **what is being done and why** without opening another file. Component-level detail (per-class contracts, DAG, sequence) lives in `components/<class>.md` and `components/_overview.md`.

```markdown
# <Feature Name>

## Context & Objective                                [Phase 1]
Context:
  - existing system state, smells, downstream consumers
Objective:
  - one-line session deliverable

## Purpose                                            [Phase 1]
Why this change exists — the problem solved and the value delivered, in 2-4
lines of plain English. No component detail.

## Core Summary                                       [Phase 1, refined]
The whole change in one read: what is being built and why, the solution shape
at a glance. Component-level detail lives in components/<class>.md and
components/_overview.md — link, don't restate.

## Functional ACs                                     [Phase 1]
Part of change set: <2-line umbrella description>

### N. <Feature heading>
    Class: <ClassName(s)>
    - N.A — <Title>. <What>. *Why:* <reason>

## Key Findings                                       [Phase 1 · research]
What investigation surfaced that shaped the design — from research/*.md,
traces, and session exploration. One bullet per finding, with its source.
  - <finding> (see research/<name>.md)

## Decision Log                                       [Phase 1 → all phases]
Strategic, functional-level decisions taken during planning — the forks we
chose and why. Appended as decisions are made.
  - <decision>. *Why:* <rationale>. *Alternatives:* <what was rejected>

## Directory Structure                                [Phase 3]
src/ file tree with per-file annotation (NEW | MODIFIED | DELETED)
tests/ file tree mirroring implementation
```

### components/<class_name>.md

See Contract Block Format in `phase_4_contracts_and_tests.md` for the full template.

### components/_overview.md

```markdown
# Components Overview

## Component Summary                                  [Phase 2]
For ≤6 classes use tables; for >6 (or multi-line ACs) use the Phase 2 block
form (preserve the bullets, don't collapse — see `phase_2_topology.md`).

**Grouping rule (binding):** NEVER one flat table mixing services, repos, and
utils in arbitrary order. Split into one `###` sub-heading per logical group —
a service together with the internals/repos/utils that change with it — so a
related change set reads as one unit. Within a group: the Service row first,
then its internals. Order groups by the feature's flow (read path before write
path, producers before consumers).

### <Group — e.g. reelAnalytics (read-path extraction)>
| # | Class | Type | Class AC (responsibility) | Necessitated by |
|---|---|---|---|---|
| 3.1 | ReelAnalyticsService | Service | Owns the read-side analytics cut | 1.A — region on every reel |
| 3.2 | CreatorBaselineMetricsRepository | Repository | Owns baseline metric rows | 1.A — region on every reel |

### <Group — e.g. timelineMetrics (shared math)>
| # | Class | Type | Class AC (responsibility) | Necessitated by |
|---|---|---|---|---|
| 3.3 | TimelineMetricsService | Service | Owns per-period timeline math | 2.B — per-period growth series |

## Injection DAG                                      [Phase 5]
> Authoritative: ../dag.mmd (when >8 nodes)

Edge inventory (by layer):
  L0 → L1: Source → Target
  ...

## App Integration                                    [Phase 5]
Integration type, wiring location, downstream call chain (ASCII)

## Sequence Diagram                                   [Phase 6]
ASCII inline (full call flow)
> Mermaid: ../sequence.mmd

## AC Traceability Matrix                             [Phase 4 end]
Feature AC → Class AC → Function AC → AC Test
(references by file/section, no restating)
```

### tasks.md

```markdown
# Tasks

## <tag> | <Action> | <Target>
Status: pending | in_progress | complete

Feature ACs: <ref> — <title>, <ref> — <title>
Class AC: <from objective.md summary>
Component file: ./components/<class_name>.md
Integration point: <from _overview.md>

Test hierarchy:
  AC Tests (primary):
    - <test name> (proves AC-N.1 with 1 line reminder)
  Branch Tests (secondary):
    - <test name>
```

---

## Change Propagation Guide (binding for agents)

When a design change occurs mid-session (user feedback, discovered constraint, re-sign-off), multiple files may need updating. This table shows what to update when each type of change happens:

```
┌─────────────────────────────────┬──────────────────────────────────────────────────┐
│ What changed                    │ Files to update                                  │
├─────────────────────────────────┼──────────────────────────────────────────────────┤
│ Feature AC added/modified       │ objective.md (Feature AC list)                   │
│                                 │ components/<affected>.md (if Function ACs shift) │
│                                 │ components/_overview.md (traceability matrix)    │
│                                 │ tasks.md (Feature AC refs on affected tasks)     │
├─────────────────────────────────┼──────────────────────────────────────────────────┤
│ Class added/removed/renamed     │ _overview.md (summary table); objective.md (dir) │
│                                 │ components/<class>.md (create/delete/rename)      │
│                                 │ components/_overview.md (DAG, sequence, matrix)  │
│                                 │ tasks.md (add/remove/rename task)                │
│                                 │ dag.mmd (node added/removed)                     │
│                                 │ sequence.mmd (participant added/removed)         │
├─────────────────────────────────┼──────────────────────────────────────────────────┤
│ Method signature changed        │ components/<class>.md (contract + Function ACs)  │
│                                 │ components/_overview.md (sequence if call changes)│
│                                 │ sequence.mmd (if call changes)                   │
├─────────────────────────────────┼──────────────────────────────────────────────────┤
│ Constructor dependency changed  │ components/<class>.md (constructor block)         │
│                                 │ components/_overview.md (DAG edge inventory)     │
│                                 │ dag.mmd (edge added/removed)                     │
├─────────────────────────────────┼──────────────────────────────────────────────────┤
│ Test added/removed              │ components/<class>.md (test list)                 │
│                                 │ components/_overview.md (traceability tally)     │
│                                 │ tasks.md (test hierarchy on affected task)       │
├─────────────────────────────────┼──────────────────────────────────────────────────┤
│ Model fields changed            │ components/<class>.md (models section)            │
│                                 │ (no cascade unless signature changes)            │
└─────────────────────────────────┴──────────────────────────────────────────────────┘
```

**Rule: after any change, walk this table and update ALL affected files before presenting the next gate.** Never leave files out of sync — the schematic is the source of truth, and a partially-updated schematic is a lie.

**Simplicity check:** if a single change requires updating more than 4 files, STOP and flag it to the user. This usually means the change is larger than it appears and may need re-scoping rather than patching across the schematic.

---

## Architecture Principles

All components use **constructor injection** forming a **complete acyclic DAG** — no cycles, no service locators, no runtime resolution. The end result reads like a self-describing book: communicative and obvious. Naming is non-negotiable (CLAUDE.md).

**Component type vocabulary:** see `reference/component_types.md` for the full Service / PipelineService / RequestPipelineService / Controller / Router / Factory / Repository / Validator / Resolver / Client / NounVerber taxonomy, plus banned suffixes and the stacked-suffix anti-pattern.

---

## Source of Truth

The schematic IS the design. Implementation follows it. If code diverges from the schematic, the schematic is corrected first (with sign-off), then the code. At the end of implementation the schematic is a faithful record of what was built.

Operationalised via `schematic-task-done --matched [y|n] --updated [y|n]` — forces explicit drift reporting per task. Silent "done" is impossible.

---

## Rules

- ⚠️ **Exception swallowing**: Any swallowed exception, silent empty-return, or defensive fallback MUST be flagged to the user for explicit sign-off.
- ⚠️ **Optional types**: Any nullable/optional return type must be explicitly signed off with justification.
- **Never proceed** to the next phase without explicit user confirmation.
- **Explore the codebase** if it can answer a question — don't ask the user what the code already tells you.
- **All names are binding** — public method names, parameter names, model field names, and return types are locked once signed off. Any deviation requires re-sign-off.
- **DAG integrity** — the injection graph must remain acyclic. If a proposed design introduces a cycle, flag it and redesign.
- **Code review gate** — after each class is implemented, verify alignment with the schematic and code quality standards.
- **Mark tasks complete** — after each task is implemented and reviewed, mark it complete before moving to the next. The user must always be able to see progress.
