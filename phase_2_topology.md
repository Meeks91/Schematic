# Phase 2: Topology

> **CLI gate commands:**
> - `schematic phase audit --schematic <name> 2 "clean" | "<findings>"` — after topology audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 2` — on user `y`.
> - `schematic phase complete --schematic <name> 2` — immediately after sign-off.

Define what each class OWNS — produce Class ACs. Write the Component Summary to `<schematic_dir>/components/_overview.md` (NOT objective.md — that stays human-only). Max 3 classes per gate.

## Phase 2 entry — Topology Roster (BINDING — before any card)

The FIRST gate of Phase 2 is a one-shot roster of the ENTIRE proposed topology — classes AND storage — so the user sees the complete set before any 1-by-1 card batch. Without it, redundant nodes and invisible surfaces (e.g. an undesigned table) slip through batch-by-batch presentation.

**Format — vertically stacked feature composites**, one strip per Phase-1 feature, in feature order. The stack IS the top-down view of the whole topology:

```
F4 — <feature title>                                        (4.A 4.B 4.C)
│
├─ <ClassName>              <Type>         [NEW|MOD]  <one-line role>
├─ ↩ <ClassName> (F1)                                 ← back-ref, no one-liner
└─ ⛁ <table name>           Table          [NEW|SHARED|FORK OPEN]  <one-line>
```

Rules:
- **Node one-liner on FIRST appearance only**; a node a later feature reuses appears as a bare back-ref (`↩ Name (Fn)`) — no duplication; the back-refs render cross-feature sharing visible.
- **Storage rows (⛁) mandatory**: any feature that persists anything must show its table(s). A persisting strip with no ⛁ row is a gate-blocking hole. Unresolved storage forks are marked `[FORK OPEN]` — never silently decided.
- **Edges are loose "uses" indentation, not wiring** — the roster promises the SET, not the arrows (the P5 DAG owns edges).
- **Names are predictions**: locking the roster locks the inventory, not designs. Nodes still die/merge/split/rename during card batches — but only via the amendment rule below, never silently.

**Draft semantics (BINDING):** the roster is a ONE-SHOT DRAFT surfaced for rapid feedback — it is NOT a design sign-off and the agent MUST NOT internalise it as commitment. The user's `y` on the roster gate means only "the set looks complete enough to start carding". The file carries a `status: DRAFT` banner until Phase 2 completes. The agent must not defend its own predictions during feedback — user edits win by default; every prediction is expected to be cheap to overturn at its card. (The roster is built inline by the planning agent — session context beats a cold subagent — but is treated as external draft input, not as the agent's design position.)

**Editable artifact (interactive-first):** render the roster as `<schematic_dir>/roster.mmd` — one Mermaid subgraph per feature, vertically stacked (chain subgraphs with invisible `~~~` links), classes as boxes, storage as cylinders, classDefs for locked/new/mod/storage/fork-open/back-ref — and **launch the visual editor on it** (`python3 <skill_dir>/reference/mermaid_edit/bridge.py <path>`, backgrounded). The round-trip IS the feedback loop: user edits (rename/kill/add nodes), hits Save & Close → re-read the file and **echo the delta back as absorbed decisions** ("killed X, renamed Y→Z, added table W to F6") before locking. Never absorb an edit silently. `components/_roster.md` holds only the status banner, legend, and the amendments log — never a duplicate of the diagram.

**Amendment rule (post-lock):** any add/kill/merge/rename discovered during card batches = an explicit `Roster amendment: <delta>` line at that gate AND an edit to `_roster.md`. The phase-end audit checks card-set ≡ roster + amendments.

The roster is its own gate — end it with **Confirm: y/comment**.

**Component Summary grouping (binding):** never one flat table mixing services, repos, and utils. One `###` sub-heading per logical group — a service plus the internals that change with it — Service row first, then its internals; groups ordered by the feature's flow. Template: `SKILL.md` → `components/_overview.md`.

## Component Card Format (BINDING — every class)

Every class is presented as a **boxed card**. The box surfaces the same surfaces every time so the user can scan a card cold and immediately see (1) what changes, (2) why, (3) what the class does, (4) where it fails loud. Apply the same shape to the in-chat presentation AND the on-disk `components/_overview.md` block.

```
┌─────────────────────────────────────────────────────────────────┐
│ 3.N  <ClassName>                                     [NEW]      │
├─────────────────────────────────────────────────────────────────┤
│ Type:               <NounVerber | Service | Factory | ...>      │
│ Lives in:           <path/relative/to/src>                      │
├─────────────────────────────────────────────────────────────────┤
│ Necessitated by:                                                │
│   • 1.A — <one-line of the Feature AC text, for context>        │
│   • 1.C — <one-line of the Feature AC text, for context>        │
├─────────────────────────────────────────────────────────────────┤
│ Purpose:                                                        │
│   • <ownership bullet — concern/domain, not interface>          │
│   • <ownership bullet>                                          │
│   • <ownership bullet>                                          │
├─────────────────────────────────────────────────────────────────┤
│ Failure modes:        (omit section if N/A)                     │
│   • <how the class fails loud — what raises, what propagates>   │
│   • <invariant that triggers a raise>                           │
├─────────────────────────────────────────────────────────────────┤
│ Service Classification Gate:                                    │
│   Domain owner:           yes | no — <one-line rationale>       │
│   Other-Service consumer: yes | no — <one-line rationale>       │
│   Decision:               <NounVerber internal | Service | ...> │
└─────────────────────────────────────────────────────────────────┘
```

**Status badges (top-right):** `[NEW]`, `[MODIFIED]`, `[DELETED]`. For `[MODIFIED]`, the `Purpose:` section splits into:
```
│ Purpose:                                                        │
│   Existing:                                                     │
│     • <unchanged ownership>                                     │
│   Added:                                                        │
│     • <what this change brings>                                 │
```

**Fields (binding):** Name · Component type · Necessitated by (refs + inline AC text) · Purpose (ownership bullets) · Failure modes (if any) · Service Classification Gate.

> **Why inline AC text in Necessitated by:** a bare `1.A, 1.C` ref forces the reader to scroll back; the one-line gloss keeps them present in *why* this class exists — the skill's core tenet.
> **Failure modes vs. Purpose:** Failure modes = what raises and propagates (hard-fail behaviour). Scope guards ("never owns sessions") belong as a short `Never:` trailing line under Purpose, not in Failure modes.

**Rules (binding):**

1. **Layout:** ONE boxed card per class, exactly the shape above — never split a class across two boxes, never collapse a card into a heading + prose. The same card renders in chat and lands in `components/_overview.md`.
2. **Necessitated-by bullets:** one per Phase 1b ref, **5–10 words**, names *why the feature needs this class* (the dependency), not what the class does. Must fit on one terminal line.

   **Direct-necessity rule (binding):** A Feature AC appears under a class's `Necessitated by` ONLY if that AC directly forces a code change inside *this* class. Transitive presence on the runtime chain does NOT count — otherwise every class lists every AC and the field becomes noise.

   Worked example: AC `2.C — persisted payload carries a make-it-yours entry` necessitates the Repository (serializer must emit a new key) only. The Service (calls `.persist()` without modification) and the Factory (already returns a domain object that incidentally carries the new field via a different AC) do NOT list `2.C` in their `Necessitated by`, even though both sit on the runtime chain. Without this rule a single AC propagates upstream and downstream and `Necessitated by` becomes meaningless.
3. **Purpose bullets** (the card's `Purpose:` section): 2–5 ownership bullets naming *concerns/domains*, not interfaces. Include `Never:` bullets when scope creep is plausible. No conjunctions joining unrelated concerns (`X AND Y` smell = split the class).
4. **No Phase 4 leakage:** Class ACs MUST NOT name method names, URL paths, model/return types, exception class names, HTTP verbs, status codes, or headers. Replace with the concern they represent (e.g. `"/api/v1/auth/google"` → `"auth HTTP surface"`).

**Self-check:** read the ACs aloud. If you could write the `# API:` section from them, you've leaked Phase 4. ACs describe *purpose*, not *interface*.

For **modified** existing classes: state what changes and why. For **deleted** classes: list with rationale.

## Storage Card Format (BINDING — every table)

Tables are topology nodes: they have ownership, relationships, and consumers, exactly like classes. Every [NEW] table — or any storage fork (new table vs shared table vs column addition) — gets its own boxed card in the SAME batch as the Repository that owns it. **A Repository card cannot lock while its storage card is undecided.**

```
┌─────────────────────────────────────────────────────────────────┐
│ S.N  <table_name>                          [NEW | SHARED | MOD] │
├─────────────────────────────────────────────────────────────────┤
│ One row is:   <identity in domain terms — no column DDL>        │
│ Owned by:     <Repository>          Written by: <pipeline/svc>  │
│ Read by:      <consumers>                                       │
│ Relates to:   <FK-level relationships, in words>                │
│ Semantics:    <cadence / retention / anchor model>              │
│ Fork:         <options considered + decision — or OPEN>         │
└─────────────────────────────────────────────────────────────────┘
```

**Layer split (mirrors class cards):** Phase 2 owns existence, identity (what one row IS), ownership, relationships, population/read semantics, and the fork decision. Column DDL, types, nullability, indexes, partitioning, and migrations stay in Phase 4 models. Storage forks are presented as options with a recommendation, gated like everything else. Storage cards land in `components/_overview.md` under a §Storage section.

**Component types vocabulary:** see `reference/component_types.md` for the full taxonomy (Service / PipelineService / RequestPipelineService / Controller / Router / Factory / Repository / Validator / Resolver / Client / `<Noun><Verb>er`).

**Good vs Bad example:** see `reference/good_bad_class_ac.md` for the `UserRepository` reference block.

Present max 3 classes per gate.

## Service Classification Gate (mandatory, every class)

Before locking any class as an internal helper (`utils/`, `repos/`, `resolvers/`, etc.) rather than a top-level `Service`, answer both questions:

| Question | Pass condition |
|---|---|
| Does this class own a coherent, nameable capability domain on its own (idempotency, taxonomy, scheduling, notifications, …)? | No → may be internal. **Yes → strong signal it is a Service.** |
| Does any other existing or foreseeable Service need this class directly? | No → may be internal today. **Yes → promote now** (architecture standards: "if needed by another service, promote"). |

**A class that answers Yes to either question is a Service candidate — flag it and get user sign-off.**

- **Domain ownership alone** → candidate (flag + discuss). Domain ownership does not require multiple consumers.
- **Cross-consumer need** → mandatory promotion (even with no owned domain).
- **Acceptable internal:** no nameable domain + solely decomposes one method + not foreseeable as cross-service.

## Audit hook (mandatory — at PHASE COMPLETION only)

The topology audit fires **once at the end of Phase 2** — the final per-gate `Confirm: y/comment` that closes the phase. Earlier sub-gates (each batch of ≤3 classes) do NOT trigger an audit; they only gate user content sign-off on that batch.

1. Dispatch `audits/topology_audit.md` per `audits/README.md`. Wait for return. Surface findings above sigil.
2. Record: `schematic phase audit --schematic <name> 2 "clean" | "<findings>"`

**Confirm: y/comment**

---

**Next:** `phase_3_directory.md`
