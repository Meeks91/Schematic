# End-to-End Audit (Post-Phase 7 — Full Schematic Consistency)

Final quality gate. Walk the entire schematic bundle and verify everything cross-references correctly, no orphans, no stale references, and the AC traceability pyramid is complete. Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/objective.md` (Phase 1 + directory structure)
- `<schematic_dir>/components/_overview.md` (Component Summary, traceability matrix, DAG, sequence)
- `<schematic_dir>/components/*.md` (every class contract)
- `<schematic_dir>/dag.mmd`
- `<schematic_dir>/sequence.mmd`
- `<schematic_dir>/tasks.md`

## Checks (in order)

### 1. AC traceability pyramid is complete
- **Every Feature AC** in `objective.md` §1 has ≥1 Class AC referencing it.
- **Every Class AC** has ≥1 Function AC traceable to it.
- **Every Function AC** has ≥1 AC Test.
- Cross-check against the traceability matrix in `_overview.md`.
- Flag any orphan ACs at any level.

### 2. Topology integrity
- Every class in `components/_overview.md` §Component Summary has a corresponding `components/<class>.md` file.
- Every `components/<class>.md` file is referenced from the Component Summary.
- Class numbering is contiguous (no gaps unless explicitly noted).
- Counts match: Component Summary rows = component files (excluding `_overview.md`) = entries in `objective.md` §Directory Structure.

### 3. DAG integrity
- Every class in the Component Summary appears in `dag.mmd` (modulo FE/BE split).
- Every edge in `dag.mmd` matches a constructor dependency in some `components/<class>.md`.
- Graph is acyclic (no cycles).
- No orphan nodes (every node has either an inbound or outbound edge — except L0 leaves).

### 4. Sequence integrity (recap from sequence_audit)
- Every flow covers a Feature AC.
- Every call matches a Function AC.
- Every participant matches a topology class.

### 5. Tasks integrity
- Every class in the Component Summary has a corresponding task in `tasks.md` (excluding FE classes already covered by FE tasks).
- Every task references the correct `components/<class>.md` file.
- Every task names the Feature ACs it satisfies — those references match `objective.md` §1.
- Task dependencies form a valid order (no task blocks-by a later-numbered task).

### 6. Stale references
- Search for class names that were renamed during the design — flag any remaining stale name.
- Search for "TODO", "TBD", "(pending)" in any locked artifact — flag for resolution.

### 7. Banned terminology drift (conditional)
- ONLY if the project's CLAUDE.md, the resolved standards modules, or the schematic's Decision Log
  ban specific terms, search every locked artifact for them.
- Skip this check entirely when no banned-term list exists — do NOT invent one.

### 8. Deferred items are explicit
- Any Feature AC marked DEFERRED must have a corresponding 501-return note in the contract.
- Flag silent deferrals.

### 9. Count tally
Report final counts:
- Feature ACs: N (X deferred, Y active)
- Classes: N (BE: X, FE: Y)
- Function ACs: ~N
- AC Tests: ~N
- Branch Tests: ~N
- Tasks: N

## Output

Return findings strictly in the format from `audits/_format.md`.

If clean, return:
```
✓ Clean

Counts: <tally>
```
