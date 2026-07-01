# Phase 6: Sequence Diagram

> **CLI gate commands:**
> - `schematic mermaid` — validate the `.mmd` diagram after writing it.
> - `schematic phase audit --schematic <name> 6 "clean" | "<findings>"` — after sequence audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 6` — on user `y`.
> - `schematic phase complete --schematic <name> 6` — immediately after sign-off.

Write ASCII sequence to `<schematic_dir>/components/_overview.md`. Write Mermaid to `<schematic_dir>/sequence.mmd`.

> **Gate enforcement:** `schematic phase complete` will reject if `sequence.mmd` does not exist, if `components/_overview.md` does not contain `## Sequence Diagram`, **or if `sequence.mmd` fails mermaid validation** — the diagram must parse before the phase can lock.

> **Surface the visual tools (mandatory, once per phase):** when presenting the sequence gate, tell the user the diagram is viewable and hand-editable right now — `schematic overview` renders it in the dashboard (Diagrams tab), and the live editor below round-trips it on disk. Don't leave these discoverable-only.

Produce the sequence diagram in **two formats**:

1. **ASCII** — rendered in the terminal for immediate review
2. **Mermaid** — output as a fenced `mermaid` code block for visual editor paste

If the user edits the Mermaid and pastes it back, that becomes the new source of truth.

## Mermaid Theme Requirements

- The schematic dashboard is dark by default; Mermaid diagrams must render correctly in dark mode.
- Do not use light `rect rgb(...)`, light node fills, or pale backgrounds that wash out dark-theme text.
- Prefer Mermaid's default dark theme styling. If grouping frames or custom colours are necessary, use dark fills with sufficient contrast.

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
3. Re-read <schematic_dir>/sequence.mmd — it now holds the user's edits. That is
   the new source of truth. Re-run `schematic mermaid` to validate it.
4. Drain any questions the user asked in the editor's Q&A bubble:
   `schematic questions` lists them with full design context;
   `schematic answer <id> "<text>"` replies into the UI live.
```

The editor handles **very large** sequence diagrams: mermaid `maxTextSize` is
raised to 5,000,000 chars and `maxEdges` to 100,000, with zoom/pan controls and a
debounced render so large diagrams stay navigable and don't thrash on each keystroke.

## ASCII Quality Requirements

- Participants spaced wide across the top with clear column separation
- Lifelines as continuous `│` columns — perfectly aligned vertically
- Method calls as solid arrows `────────────────►` with method name + cascading parameters **above** the arrow
- Return values as dashed arrows `◄─ ─ ─ ─ ─ ─ ─ ─` with return type **above** the arrow
- Loop/branch frames as clearly boxed regions with label
- Generous vertical spacing between interactions
- **Driving AC ref on each major flow segment** — label the loop/branch frame (or the opening call of a distinct sub-flow) with the Feature AC it realises (e.g. frame title `verify token  [<AC>]`). Keeps the call flow tied to the intent it proves, not just the mechanics.

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
2. Record: `schematic phase audit --schematic <name> 6 "clean" | "<findings>"`

**Confirm: y/comment**

---

**Next:** `phase_7_tasks.md`
