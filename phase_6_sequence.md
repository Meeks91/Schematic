# Phase 6: Sequence Diagram

> **CLI gate commands:**
> - `schematic mermaid` — validate the `.mmd` diagram after writing it.
> - `schematic phase audit --schematic <name> 6 "clean" | "<findings>"` — after sequence audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 6` — on user `y`.
> - `schematic phase complete --schematic <name> 6` — immediately after sign-off.

Write ASCII sequence to `<schematic_dir>/components/_overview.md`. Write Mermaid to `<schematic_dir>/sequence.mmd`. In `components/_overview.md` § Sequence Diagram, also list every flow file with its purpose and the ACs it covers.

> **Multi-flow features → one `.mmd` per flow (user rule 2026-07-22).** When the feature has
> several distinct runtime flows, do NOT pack them into one diagram: `sequence.mmd` holds the
> primary flow; siblings are `sequence_<flow>.mmd` beside it. All validate via `schematic mermaid`
> (it scans every `.mmd` in the dir) and each renders as its own entry ("tab") in the dashboard's
> Diagrams view. `_overview.md`'s `## Sequence Diagram` header lists every file with its flow + ACs.
> Open the live editor per file, sequentially — Save & Close advances to the next.
> (Future tooling: multi-tab support inside `reference/mermaid_edit/` — not built yet.)

> **Gate enforcement:** `schematic phase complete` will reject if `sequence.mmd` does not exist, if `components/_overview.md` does not contain `## Sequence Diagram`, **or if `sequence.mmd` fails mermaid validation** — the diagram must parse before the phase can lock.

> **Surface the visual tools (mandatory, once per phase):** when presenting the sequence gate, tell the user the diagram is viewable and hand-editable right now — `schematic overview` renders it in the dashboard (Diagrams tab), and the live editor below round-trips it on disk. Don't leave these discoverable-only.

**Presentation (BINDING — user rule 2026-07-15):** ALWAYS create the Mermaid diagram (`sequence.mmd`, validated) and AUTO-OPEN it in the schematic editor — no asking (`python3 <skill_dir>/reference/mermaid_edit/bridge.py <schematic_dir>/sequence.mmd`, backgrounded, + arm the Q&A watcher). The user reviews the diagram in the editor BEFORE the gate's Confirm — never present a diagram gate the user hasn't been shown. Never hand-draw ASCII graph art in chat. The on-disk `.mmd` is the source of truth; editor saves round-trip to it. Every diagram marks new / changed / removed calls per § Change Status Colours.

## Mermaid Theme Requirements

- The schematic dashboard is dark by default; Mermaid diagrams must render correctly in dark mode.
- Do not use light `rect rgb(...)`, light node fills, or pale backgrounds that wash out dark-theme text.
- Prefer Mermaid's default dark theme styling. If grouping frames or custom colours are necessary, use dark fills with sufficient contrast.

## Change Status Colours (BINDING — user rule 2026-10-04)

Every sequence diagram marks what the feature changes with Mermaid `rect` boxes (dark fills only):

| Status | Box | Covers |
|---|---|---|
| NEW | `rect rgb(20, 83, 45)` (dark green) | new call, rule, or branch |
| CHANGED | `rect rgb(120, 53, 15)` (dark amber) | existing call with new args / behaviour / fields |
| REMOVED | `rect rgb(127, 29, 29)` (dark red) | existing call the flow drops — only when showing it helps; message text prefixed `REMOVED:` |
| unchanged | no box | existing call, as-is |

- **Key line first:** every diagram opens with `Note over <first>,<last>: KEY · green box = NEW call or rule · amber box = CHANGED call · red box = REMOVED · no box = unchanged` — drop the red clause when the diagram has no removed calls.
- **Never straddle a branch:** a `rect` cannot split an `alt`/`else` or `par`/`and` frame — put the rects INSIDE each branch. A `rect` may wrap a whole `alt`/`par` only when every branch shares the same status.
- **Rules box too:** a new rule shown as a self-call gets a green `rect` (see § Readable Diagrams).

```
Note over MIY,Req: KEY · green box = NEW call or rule · amber box = CHANGED call · no box = unchanged
rect rgb(120, 53, 15)
    MIY->>Gen: generate(request)
end
rect rgb(20, 83, 45)
    Gen->>Req: top_comments (same ≤ 50)
end
alt zero candidates
    rect rgb(20, 83, 45)
        Gen-->>MIY: empty (no judge call)
    end
else
    rect rgb(120, 53, 15)
        Gen-->>MIY: candidates
    end
end
```

## Visual round-trip editor (bundled)

This skill bundles a live-preview Mermaid editor at `reference/mermaid_edit/`
(`bridge.py` + `editor.html`, stdlib-only, no deps). Offer it whenever the user
wants to hand-edit `sequence.mmd` instead of pasting — it round-trips the file on
disk, so the saved version is picked up automatically.

```
1. Write the diagram to <schematic_dir>/sequence.mmd (you already do this).
2. Launch the editor — it serves the page, opens the browser, blocks until Save & Close:

     python3 <skill_dir>/reference/mermaid_edit/bridge.py <schematic_dir>/sequence.mmd

   Run it backgrounded (Ctrl+S in the editor saves without closing; the "Save &
   Close" button ends the session). You are notified on exit, which prints
   "Saved: <path>" plus a count of any unanswered editor questions.
3. ARM THE Q&A WATCHER in the same moment (BINDING — see SKILL.md):

     python3 <skill_dir>/reference/mermaid_edit/watcher.py <schematic_dir>/sequence.mmd

   Also backgrounded. It exits when an unanswered bubble question lands — on
   that wake-up: `schematic questions` → `schematic answer <id> "<text>"` →
   re-arm the watcher. Without it, bubble questions sit unanswered (dead air).
4. Re-read <schematic_dir>/sequence.mmd — it now holds the user's edits. That is
   the new source of truth. Re-run `schematic mermaid` to validate it.
5. Drain any remaining questions from the editor's Q&A bubble:
   `schematic questions` lists them with full design context;
   `schematic answer <id> "<text>"` replies into the UI live.
```

The editor handles **very large** sequence diagrams: mermaid `maxTextSize` is
raised to 5,000,000 chars and `maxEdges` to 100,000, with zoom/pan controls and a
debounced render so large diagrams stay navigable and don't thrash on each keystroke.

**No disk reload:** the open editor does NOT pick up edits made to the `.mmd` on disk — a Save in the editor overwrites them. Stop the bridge (and its watcher) before editing the file outside the editor, then relaunch both.

## ASCII Quality Requirements

- Participants spaced wide across the top with clear column separation
- Lifelines as continuous `│` columns — perfectly aligned vertically
- Method calls as solid arrows `────────────────►` with method name + cascading parameters **above** the arrow
- Return values as dashed arrows `◄─ ─ ─ ─ ─ ─ ─ ─` with return type **above** the arrow
- Loop/branch frames as clearly boxed regions with label
- Generous vertical spacing between interactions
- Change status mirrors the Mermaid boxes: suffix NEW calls `★`, CHANGED `~`, REMOVED `✗` (unchanged unmarked)

## Readable Diagrams (BINDING — user rule 2026-10-29)

- **Calls keep their signed names.** Every arrow is the real method from the contract card (`calculateConvictionModel(groupContainer, adjustments)`); returns are the real type. Participants are the real class names.
- **Self-arrows for internal steps.** A rule the receiver applies itself is a self-call (`CMC->>CMC: scaledTo(target exposure)`), not a Note.
- **No grey Notes** beyond the KEY line. A rule worth showing is a call or a self-call; detail lives in the contract card.
- **Branch conditions in plain English.** Write the condition after the keyword as a full clause: `alt the request has conviction model settings` / `else the request has no conviction model settings` / `opt the request is a report` / `loop for each day and each group`. The renderer prints them as `IF …` / `ELSE …` / `IF ONLY …` / `LOOP …` (`reference/mermaid_edit/sequence-frame-labels.js`); every frame gets a blue dotted border and blue branch text.
- **`autonumber`** on every sequence diagram so a step can be named by number.
- **No AC tags** on calls, frames or notes — the traceability matrix in `components/_overview.md` maps every AC.
- **Enforced mechanically, not by review.** `schematic mermaid` fails any sequence diagram that breaks these rules, and `phase complete` refuses an invalid `.mmd`: no `autonumber`, an AC tag, a Note other than the KEY line, a branch condition under 3 words, a call with more than 3 arguments (elide the rest as `…`), or a call label repeated verbatim (draw a pass-through hop once, the next as `…`).

## Supplementary: Concurrency Diagram (when applicable)

If the feature involves parallelism, produce a separate concurrency diagram showing fork point, parallel work, join point, and sequential before/after.

## Contract Validation Checkpoint

Walk through the sequence diagram and verify:
- Every method call matches a public function defined in Phase 4
- Every parameter and return type is consistent with the contracts
- No calls exist that weren't declared in the contracts
- The injection DAG from Phase 5 supports every call direction

## Sequence Consistency Validation

Explore the codebase and verify:
- **Call pattern consistency**: Does the sequence flow match how existing pipelines delegate work?
- **Method naming consistency**: Do method names follow the same verb conventions as existing components?
- **Return flow consistency**: Do return types flow back the same way existing pipelines return results?
- **Error propagation consistency**: Does exception flow match existing patterns?

Flag deviations to the user. This catches "looks right in isolation but doesn't match how this codebase flows."

## Audit hook (mandatory — at PHASE COMPLETION only)

The sequence audit fires **once at the end of Phase 6** — the final per-flow `Confirm: y/comment` that closes the phase. Earlier sequence sub-gates do NOT trigger an audit; they only gate user content sign-off on each flow.

1. Dispatch `audits/sequence_audit.md` per `audits/README.md`. Wait for return. Surface findings above sigil.
2. **Blind-spot pass (post-sequence):** dispatch a SEPARATE agent per `audits/_blind_spot_discovery.md` on the same P6 dispatch — injected with `sequence.mmd` + the full schematic + codebase access. Now the full runtime flow is drawn, it assesses **blast radius** over entry points, callers, and touched state. Surface candidates above the sigil; each is dispositioned (promote → task / deferral **via the Change Propagation Guide in `SKILL.md`**, or dismiss) as part of this sign-off. Advisory, non-gating, stateless.
3. Record: `schematic phase audit --schematic <name> 6 "clean" | "<findings>"`

**Confirm: y/comment**

---

**Next:** `phase_7_tasks.md`
