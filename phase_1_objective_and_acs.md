# Phase 1: Feature Spec + Feature ACs

> **CLI gate commands** (run at the noted moments — see `SKILL.md` Approval Gate):
> - `schematic init <name>` — scaffold the bundle BEFORE drafting anything.
> - `schematic phase audit --schematic <name> 1 "clean" | "<findings>"` — after audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 1` — on user `y`.
> - `schematic phase complete --schematic <name> 1` — immediately after sign-off.

The goal of this phase is to reach a **shared, precise understanding of what is being built and why** — producing Feature ACs.

This phase writes to `<schematic_dir>/objective.md` §1 (Context, Objective) and §1b (Feature Change List + Feature ACs).

## Phase 1 entry — branch by session state

**If this is a fresh planning session (no prior context):** GRILL FIRST.
Interview the user relentlessly about every aspect of this feature until reaching shared understanding. Walk down **every branch** of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer. Ask questions **one at a time**. If a question can be answered by exploring the codebase, explore the codebase instead.

**If picking up with existing context (resuming a build, working from a prior plan, mid-conversation):** ABSORB AND ACCELERATE.
The understanding already exists in the session. Do NOT re-derive it phase by phase. Instead:

1. Absorb everything already discussed — decisions made, classes named, responsibilities agreed, patterns identified, constraints surfaced.
2. Pre-populate as many phases as the existing context supports. If the conversation already covered topology, directory structure, or partial contracts — fill those sections in.
3. Present the pre-populated state to the user for confirmation, phase by phase (still gated, still write-on-lock). But present what you already know rather than asking questions you already have answers to.

Crystallise the starting point:

```
Context:   <one to three lines — where things stand, what's done, what remains>
Objective: <one line — what THIS session is aiming to land>
Already absorbed from session:
  - <list what you're carrying forward — e.g. "class topology for X, Y, Z",
    "Feature ACs 1-3 agreed", "directory structure discussed">
```

Then proceed from the earliest phase that still needs user sign-off — skipping phases that are already locked.

**Confirm: y/comment**

---

**Phase 1 rule — no design-question smuggling.** Phase 1 captures **intent**, not contract. Open design questions (return shapes, error propagation paths, optionality, threading models) belong in Phase 4 — surface them there.

---

## Phase 1b — Feature Change List

Produce a **numbered feature change list**. Each entry is class-anchored, with sub-changes broken out and What/Why per sub-change. This is the single locked intent document for the feature.

Format:

```
Part of change set: <max 2 lines — answers "what are we working on?" at a glance.
                     NOT a list of features. A casual one-breath description of the umbrella work>

1. <Feature heading — present-tense outcome, no method names>
   Class:   <ClassName>  (or: <ClassA> + <ClassB> + <ClassC> if multi-class)
   Changes:
     1.A
       Title: <one-line description of this sub-change>
       What:  <what the change is>
       Why:   <purpose — ties back to Context/Objective>
     1.B
       Title: <one-line description>
       What:  <what>
       Why:   <purpose>
```

Rules:
- **Change-set header mandatory**: anchors the numbered features in their umbrella context.
- **Class-anchored**: every feature change must name the class(es) it touches. Orphan changes are not allowed.
- **Title / What / Why all mandatory per sub-change**.
- **No method names, no return types, no signatures**: those are Phase 4 (contracts). Feature lines describe outcomes, not interfaces.
- **Hygiene changes explicit**: renames, test re-splits, audit-event additions are numbered entries — never hidden in implementation tasks.
- **Wording style**: short, information-dense, full sentences in plain English. Density comes from precision, not from clipping articles or verbs.
- ⚠️ **MAX 3 numbered features per gate** (see Iteration Rule in `SKILL.md`). If your change list has 5 features, present `1`-`3` first, lock, then `4`-`5`. Never present all at once. Sub-changes (1.A, 1.B) belong to their parent and do not count separately, but if a single feature has >5 sub-changes it's probably two features — split it.

### Audit hook (mandatory)

1. Dispatch `audits/ac_audit.md` per `audits/README.md`. Wait for return. Surface findings above sigil.
2. Record: `schematic phase audit --schematic <name> 1 "clean" | "<findings>"`

**Confirm: y/comment**

---

## Phase 1.5: Context Validation (Automated — not a gate)

After Feature ACs are signed off, explore the codebase and verify:

- **Naming consistency**: Do the AC names and class names match existing conventions?
- **Error handling style**: Do the failure modes match how similar components handle errors?
- **Return conventions**: Are return types consistent with existing patterns?
- **Integration fit**: Are the ACs compatible with how existing components actually work?

Read CLAUDE.md and explore relevant existing code. If mismatches are found, flag them to the user before proceeding to Phase 2.

This is a consistency check, not a gate. The user may choose to deviate intentionally.

---

**Next:** `phase_2_topology.md`
