# Phase 2: Topology

> **CLI gate commands:**
> - `schematic phase audit --schematic <name> 2 "clean" | "<findings>"` — after topology audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 2` — on user `y`.
> - `schematic phase complete --schematic <name> 2` — immediately after sign-off.

Define what each class OWNS — produce Class ACs. The roster gate is the sole design gate; once it locks, the agent auto-writes the Component Summary to `<schematic_dir>/components/_overview.md` (NOT objective.md — that stays human-only) with no further per-class gate.

## Phase 2 entry — Topology Roster (BINDING — before any card)

The FIRST gate of Phase 2 is a one-shot roster of the ENTIRE proposed topology — classes AND storage — so the user sees and signs off the complete set at once. It is the phase's only design gate: there is no subsequent per-class card batch; the cards are auto-written from the locked roster (below). Without it, redundant nodes and invisible surfaces (e.g. an undesigned table) slip through.

**Format — vertically stacked feature composites**, one strip per Phase-1 feature, in feature order. The stack IS the top-down view of the whole topology:

```
F4 — <feature title>                                        (4.A 4.B 4.C)
│
├─ <ClassName>              <Type>         [NEW|MOD]  <one-line role>
├─ ↩ <ClassName> (F1)                                 ← back-ref, no one-liner
└─ ⛁ <table name>           Table          [NEW|SHARED|MOD]  <one-line>
```

Rules:
- **Node one-liner on FIRST appearance only**; a node a later feature reuses appears as a bare back-ref (`↩ Name (Fn)`) — no duplication; the back-refs render cross-feature sharing visible.
- **Storage rows (⛁) mandatory**: any feature that persists anything must show its table(s). A persisting strip with no ⛁ row is a gate-blocking hole. **Forks are resolved BEFORE the roster** (Question/Why + recommendation, gated, logged in the Decision Log) — a `[FORK OPEN]` node on the roster is forbidden; and **every node label is plain English a reader understands cold** (what it is / what it answers), never internal shorthand like "rostered predicate".
- **Edges are loose, labelled "uses" arrows, not wiring** — every strip draws `A -->|"what A asks of B"| B` between its nodes, including into its `↩` back-refs, so the reader sees how the bundle connects; a strip of unconnected boxes is a gate-blocking hole. The arrows are predictions the P5 DAG re-derives (P5 owns injection edges); locking the roster locks the SET, not the arrows.
- **Type is decided HERE**: every node label carries its component type, and the roster gate is where that type locks. For any node whose type is contestable (internal helper vs top-level `Service`), the Service Classification Gate questions (below) are asked and answered ON this gate — there is no later per-class classification gate.
- **Names are predictions**: locking the roster locks the inventory, not designs. Nodes still die/merge/split/rename during the auto-write — but only via the amendment rule below, never silently.

**Draft semantics (BINDING):** the roster is a ONE-SHOT DRAFT surfaced for rapid feedback — the agent MUST NOT internalise the names and purposes as commitment. The user's `y` on the roster gate locks the SET and each node's TYPE; names and purposes stay predictions, overturned only via the amendment rule. The file carries a `status: DRAFT` banner until Phase 2 completes. The agent must not defend its own predictions during feedback — user edits win by default; every prediction is expected to be cheap to overturn at its card. (The roster is built inline by the planning agent — session context beats a cold subagent — but is treated as external draft input, not as the agent's design position.)

**Editable artifact (interactive-first):** render the roster as `<schematic_dir>/roster.mmd` — one Mermaid subgraph per feature, vertically stacked (chain subgraphs with invisible `~~~` links), classes as boxes, storage as cylinders, classDefs for locked/new/mod/storage/fork-open/back-ref (**dark-mode safe, BINDING**: the editor is dark-themed and its label colour overrides `color:` — use dark fills + white text + status colour on the stroke, e.g. `classDef new fill:#14532d,stroke:#4ade80,color:#fff`; never pastel/white fills; **validate with `schematic mermaid --file <path>` after EVERY write — never nest `"` inside a `["…"]` or `|"…"|` label**) — and **launch the visual editor on it** (`python3 <skill_dir>/reference/mermaid_edit/bridge.py <path>`, backgrounded) **paired with the Q&A watcher** (`python3 <skill_dir>/reference/mermaid_edit/watcher.py <path>`, backgrounded — BINDING, see SKILL.md; re-arm after each answer). The round-trip IS the feedback loop: user edits (rename/kill/add nodes), hits Save & Close → re-read the file and **echo the delta back as absorbed decisions** ("killed X, renamed Y→Z, added table W to F6") before locking. Never absorb an edit silently. On Save & Close (bridge exit) the bridge also prints every sticky note (`NOTE (x=…,y=…): …` lines, mirrored in `<diagram>.notes.json`) — read and disposition EVERY note before the gate (absorb → amendment, or answer it), never leave one unread. `components/_roster.md` holds only the status banner, legend, and the amendments log — never a duplicate of the diagram.

**Amendment rule (post-lock):** any add/kill/merge/rename discovered during the auto-write = an explicit `Roster amendment: <delta>` line in `_roster.md`, surfaced at the phase-closing Confirm. The phase-end audit checks card-set ≡ roster + amendments.

The roster is its own gate — end it with **Confirm: y/comment**.

**Component Summary grouping (binding):** the Component Summary is auto-written to `components/_overview.md` once the roster locks — no separate gate. Never one flat table mixing services, repos, and utils. One `###` sub-heading per logical group — a service plus the internals that change with it — Service row first, then its internals; groups ordered by the feature's flow. Template: `SKILL.md` → `components/_overview.md`.

## Component Card Format (BINDING — every class)

Each class MAY carry a **boxed card** as optional detail beneath its Component Summary row — the agent's choice per class, no gate. When written, it takes exactly the shape below so a reader scans it cold and sees (1) what changes, (2) why, (3) what the class owns. The card is auto-written to `components/_overview.md` alongside the summary — never presented in chat for a separate sign-off.

```text
┌─────────────────────────────────────────────────────────────────┐
│ 3.N  <ClassName>                                          [NEW] │
├─────────────────────────────────────────────────────────────────┤
│ Type:        <NounVerber | Service | Factory | ...>             │
│ Lives in:    <path/relative/to/src>                             │
├─────────────────────────────────────────────────────────────────┤
│ Necessitated by:                                                │
│   1.A · <one-line of the Feature AC text, for context>          │
│   1.C · <one-line of the Feature AC text, for context>          │
├─────────────────────────────────────────────────────────────────┤
│ Purpose:                                                        │
│   · <ownership bullet — concern/domain, not interface>          │
│   · <ownership bullet>                                          │
│   · <ownership bullet>                                          │
├─────────────────────────────────────────────────────────────────┤
│ Service Classification Gate:                                    │
│   Domain owner:            yes | no — <one-line rationale>      │
│   Other-Service consumer:  yes | no — <one-line rationale>      │
│   Decision:                <NounVerber internal | Service ...>  │
└─────────────────────────────────────────────────────────────────┘
```

**Status badges (top-right):** `[NEW]`, `[MODIFIED]`, `[DELETED]`. For `[MODIFIED]`, the `Purpose:` section splits into:
```text
│ Purpose:                                                        │
│   Existing:                                                     │
│     · <unchanged ownership>                                     │
│   Added:                                                        │
│     · <what this change brings>                                 │
```

**Fields (binding):** Name · Component type · Necessitated by (refs + inline AC text) · Purpose (ownership bullets) · Service Classification Gate.

> **Why inline AC text in Necessitated by:** a bare `1.A, 1.C` ref forces the reader to scroll back; the one-line gloss keeps them present in *why* this class exists — the skill's core tenet.
> **Scope guards:** what a class does NOT own ("never owns sessions") belongs as a short `Never:` trailing line under Purpose.
> **Failure modes are NOT designed here** — they are designed in Phase 4 with the contract (what each method raises / propagates / converts).

**Rules (binding):**

1. **Layout:** ONE boxed card per class, exactly the shape above — never split a class across two boxes, never collapse a card into a heading + prose. The card is auto-written to `components/_overview.md`, never gated in chat.
2. **Necessitated-by bullets:** one per Phase 1b ref, **5–10 words**, names *why the feature needs this class* (the dependency), not what the class does. Must fit on one terminal line.

   **Direct-necessity rule (binding):** A Feature AC appears under a class's `Necessitated by` ONLY if that AC directly forces a code change inside *this* class. Transitive presence on the runtime chain does NOT count — otherwise every class lists every AC and the field becomes noise.

   Worked example: AC `2.C — persisted payload carries a make-it-yours entry` necessitates the Repository (serializer must emit a new key) only. The Service (calls `.persist()` without modification) and the Factory (already returns a domain object that incidentally carries the new field via a different AC) do NOT list `2.C` in their `Necessitated by`, even though both sit on the runtime chain. Without this rule a single AC propagates upstream and downstream and `Necessitated by` becomes meaningless.
3. **Purpose bullets** (the card's `Purpose:` section): 2–5 ownership bullets naming *concerns/domains*, not interfaces. Include `Never:` bullets when scope creep is plausible. No conjunctions joining unrelated concerns (`X AND Y` smell = split the class).
4. **No Phase 4 leakage:** Class ACs MUST NOT name method names, URL paths, model/return types, exception class names, HTTP verbs, status codes, or headers. Replace with the concern they represent (e.g. `"/api/v1/auth/google"` → `"auth HTTP surface"`).

**Self-check:** read the ACs aloud. If you could write the `# API:` section from them, you've leaked Phase 4. ACs describe *purpose*, not *interface*.

For **modified** existing classes: state what changes and why. For **deleted** classes: list with rationale.

## Storage Card Format (BINDING — every table)

Tables are topology nodes: they have ownership, relationships, and consumers, exactly like classes. Every [NEW] table — or any storage fork (new table vs shared table vs column addition) — gets its own boxed card, MANDATORY per table and auto-written alongside the Repository that owns it. **A Repository cannot lock on the roster while its table's fork is undecided** (forks are resolved before the roster).

```text
┌─────────────────────────────────────────────────────────────────┐
│ S.N  <table_name>                          [NEW | SHARED | MOD] │
├─────────────────────────────────────────────────────────────────┤
│ One row is:                                                     │
│   <identity in domain terms — no column DDL>                    │
├─────────────────────────────────────────────────────────────────┤
│ Owned by:    <Repository>                                       │
│ Written by:  <pipeline / svc>                                   │
├─────────────────────────────────────────────────────────────────┤
│ Read by:                                                        │
│   <consumers>                                                   │
├─────────────────────────────────────────────────────────────────┤
│ Relates to:                                                     │
│   <FK-level relationships, in words>                            │
├─────────────────────────────────────────────────────────────────┤
│ Semantics:                                                      │
│   <cadence / retention / anchor model>                          │
├─────────────────────────────────────────────────────────────────┤
│ Fork:                                                           │
│   <options considered + decision — or OPEN>                     │
└─────────────────────────────────────────────────────────────────┘
```

**Layer split (mirrors class cards):** Phase 2 owns existence, identity (what one row IS), ownership, relationships, population/read semantics, and the fork decision. Column DDL, types, nullability, indexes, partitioning, and migrations stay in Phase 4 models. Storage forks are presented as options with a recommendation, decided at the roster gate. Storage cards are auto-written to `components/_overview.md` under a §Storage section.

**Component types vocabulary:** see `reference/component_types.md` for the full taxonomy (Service / PipelineService / RequestPipelineService / Controller / Router / Factory / Repository / Validator / Resolver / Client / `<Noun><Verb>er`).

**Good vs Bad example:** see `reference/good_bad_class_ac.md` for the `UserRepository` reference block.

## Service Classification Gate (mandatory, every class — decided at the roster gate)

This is the reference for the classification questions the roster gate asks (see the roster rules above). Before locking any class as an internal helper (`utils/`, `repos/`, `resolvers/`, etc.) rather than a top-level `Service`, answer both questions ON the roster gate:

| Question | Pass condition |
|---|---|
| Does this class own a coherent, nameable capability domain on its own (idempotency, taxonomy, scheduling, notifications, …)? | No → may be internal. **Yes → strong signal it is a Service.** |
| Does any other existing or foreseeable Service need this class directly? | No → may be internal today. **Yes → promote now** (architecture standards: "if needed by another service, promote"). |

**A class that answers Yes to either question is a Service candidate — flag it and get user sign-off.**

- **Domain ownership alone** → candidate (flag + discuss). Domain ownership does not require multiple consumers.
- **Cross-consumer need** → mandatory promotion (even with no owned domain).
- **Acceptable internal:** no nameable domain + solely decomposes one method + not foreseeable as cross-service.

## Audit hook (mandatory — at PHASE COMPLETION only)

The topology audit fires **once at the end of Phase 2** — after the Component Summary is auto-written, before the phase-closing `Confirm: y/comment`. Phase 2 has exactly two gates: the roster gate and this closing gate — there are no per-class sub-gates in between.

1. Dispatch `audits/topology_audit.md` per `audits/README.md`. Wait for return. Surface findings above sigil.
2. Record: `schematic phase audit --schematic <name> 2 "clean" | "<findings>"`

**Confirm: y/comment**

---

**Next:** `phase_3_directory.md`
