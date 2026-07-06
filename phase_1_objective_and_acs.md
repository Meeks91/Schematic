# Phase 1: Feature Spec + Feature ACs

> **CLI gate commands** (run at the noted moments — see `SKILL.md` Approval Gate):
> - `schematic init <name>` — scaffold the bundle BEFORE drafting anything.
> - `schematic phase audit --schematic <name> 1 "clean" | "<findings>"` — after audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 1` — on user `y`.
> - `schematic phase complete --schematic <name> 1` — immediately after sign-off.

The goal of this phase is to reach a **shared, precise understanding of what is being built and why** — producing Feature ACs.

This phase writes the human frame of `<schematic_dir>/objective.md`: Context & Objective, Purpose, Core Summary, Functional ACs (the Feature Change List below), Key Findings, and Decision Log. Component-level detail is NOT written here — it lands in `components/` from Phase 2 on.

## Phase 1 entry — branch by session state

**If this is a fresh planning session or the current context has shared understanding gaps:** PROCEED TO GRILL.
Interview the user relentlessly about every aspect of this feature until reaching shared understanding. Walk down **every branch** of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer. Ask questions **one at a time**. If a question can be answered by exploring the codebase, explore the codebase instead.

**Grill aim (binding cue):** our aim is also to uncover all **unknown knowns** we hadn't considered — to establish an exhaustive understanding of impact and what we must plan for, so we never reach **unknown unknowns** during implementation. Search and discover up front; the post-grill blind-spot pass (below) then confirms rather than discovers cold.

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

**Confirm: y/comment** *(this entry gate applies to the ABSORB path only — it confirms the crystallised starting point. The fresh-GRILL path has no entry gate; its first gate is the Phase 1b change list below.)*

---

**Phase 1 rule — no design-question smuggling.** Phase 1 captures **intent**, not contract. Open design questions (return shapes, error propagation paths, optionality, threading models) belong in Phase 4 — surface them there.

---

## Phase 1b — Feature Change List

Produce a **numbered feature change list**. Each entry is class-anchored, with sub-changes broken out and What/Why per sub-change. This is the single locked intent document for the feature.

Format — one heading + one table per feature, NEVER nested Title/What/Why prose blocks (they are unreadable at 3+ sub-changes):

```markdown
Part of change set: <max 2 lines — answers "what are we working on?" at a glance.
                     NOT a list of features. A casual one-breath description of the umbrella work>

### 1. <Feature heading — present-tense outcome, no method names>
Class: <ClassName>  (or: <ClassA> + <ClassB> + <ClassC> if multi-class)

| AC | Title | What | Why |
|---|---|---|---|
| 1.A | <one-line description> | <what the change is> | <purpose — ties back to Context/Objective> |
| 1.B | <one-line description> | <what> | <purpose> |

Notes (non-AC):
- <composition/wiring fallout that is NOT a verifiable AC — e.g. "the hook
  requires an enrichment read the assembler can't reach today; wiring lands
  in Phase 2 topology / Phase 5 injection". Omit the section when empty.>
```

Rules:
- **Change-set header mandatory**: anchors the numbered features in their umbrella context.
- **Class-anchored**: every feature change must name the class(es) it touches. Orphan changes are not allowed.
- **Table mandatory**: one row per sub-change; AC / Title / What / Why columns all populated. Keep What/Why cells to one or two sentences — if a cell needs a paragraph, the sub-change is too big; split it.
- **Notes (non-AC) section**: wiring/composition consequences live here as bullets, never disguised as ACs and never buried in a Why cell.
- **No method names, no return types, no signatures**: those are Phase 4 (contracts). Feature lines describe outcomes, not interfaces.
- **Hygiene changes explicit**: renames, test re-splits, audit-event additions are numbered entries — never hidden in implementation tasks.
- **Wording style**: short, information-dense, full sentences in plain English. Density comes from precision, not from clipping articles or verbs.
- ⚠️ **MAX 3 numbered features per gate** (see Iteration Rule in `SKILL.md`). If your change list has 5 features, present `1`-`3` first, lock, then `4`-`5`. Never present all at once. Sub-changes (1.A, 1.B) belong to their parent and do not count separately, but if a single feature has >5 sub-changes it's probably two features — split it.

### Audit hook (mandatory)

1. Dispatch `audits/ac_audit.md` per `audits/README.md`. Wait for return. Surface findings above sigil.
2. **Blind-spot pass (post-grill):** dispatch a SEPARATE agent per `audits/_blind_spot_discovery.md` on the same P1 dispatch — injected with the drafted ACs + schematic + codebase access. Now the known-knowns are locked, it hunts **unknown knowns** (missed scope, consumers, constraints). Surface candidates above the sigil; each is dispositioned (promote → Feature AC / Key Finding / Decision Log, or dismiss) as part of this sign-off. Advisory, non-gating, stateless.
3. Record: `schematic phase audit --schematic <name> 1 "clean" | "<findings>"`

**Confirm: y/comment**

---

## Phase 1c — Human frame (Purpose · Core Summary · Key Findings · Decision Log)

Alongside the change list, populate the remaining human-facing sections of `objective.md` so a reader understands the change without opening another file:

- **Purpose** — why this change exists: the problem solved and value delivered, 2-4 lines, plain English, no component detail.
- **Core Summary** — the whole change in one read: what is being built and why, the solution shape at a glance. Link to `components/` for detail; never restate it here.
- **Key Findings** — what investigation surfaced that shaped the design, drawn from `research/*.md`, traces, and session exploration. One bullet per finding, each citing its source.
- **Decision Log** — strategic, functional-level decisions taken during planning (the forks chosen and why, with alternatives rejected). Seed it here and append in later phases as decisions are made.

Written on the same Phase 1 lock as the change list. The Decision Log stays live across all phases.

---

## Phase 1.5: Context Validation (Automated — not a gate)

After Feature ACs are signed off, explore the codebase and verify:

- **Naming consistency**: Do the AC names and class names match existing conventions?
- **Error handling style**: Do the failure modes match how similar components handle errors?
- **Return conventions**: Are return types consistent with existing patterns?
- **Integration fit**: Are the ACs compatible with how existing components actually work?

Read the resolved standards modules (see `standards_resolution.md`) and explore relevant existing code. If mismatches are found, flag them to the user before proceeding to Phase 2.

This is a consistency check, not a gate. The user may choose to deviate intentionally.

---

**Next:** `phase_2_topology.md`
