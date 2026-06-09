# Sequence Audit (Phase 6 — Sequence Diagrams)

Quality gate for Phase 6. Walk the locked sequence diagrams from this gate and verify they're consistent with the contracts (Phase 4) and the DAG (Phase 5). Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/sequence.mmd` (Mermaid — authoritative)
- `<schematic_dir>/components/_overview.md` §Sequence Diagrams (ASCII rendering — must match)
- `<schematic_dir>/components/<class>.md` (contracts — referenced by every call in the diagram)
- `<schematic_dir>/dag.mmd` + `_overview.md` §Injection DAG (validates call direction)
- `/Users/micahsimmons/.claude/skills/schematic/SKILL.md` (Phase 6 + Phase 6.5/6.6 checkpoints)

## Checks (in order)

### 1. Every call exists in a contract
For each arrow in the sequence (sender → receiver: method(args)):
- The receiver class must exist in topology (`objective.md` §2).
- The method must appear in the receiver's `components/<receiver>.md` Public API.
- The args must match the method signature (param names, types).
- **Flag undocumented calls.** This is the most common drift source.

### 2. Return types flow correctly
For each return arrow (`◄ ─ ─ ─`):
- The returned type must match the method's declared return type in the contract.
- Flag type mismatches.

### 3. DAG supports every call direction
For each call `A → B`:
- `B` must be a constructor dependency of `A` per the DAG (`dag.mmd`).
- Flag calls that violate the injection DAG (A depending on B without an edge).

### 4. Error paths match Failure modes
- Notes / annotations describing error propagation must match the receiver method's Failure modes in the contract.
- Flag mismatches (e.g. diagram says "→ 422" but contract says 409).

### 5. ASCII mirrors Mermaid
- Every participant in Mermaid appears in ASCII.
- Every call in Mermaid appears in ASCII (and vice versa).
- Flag drift — Mermaid is authoritative; ASCII is the mirror.

### 6. No "skipped" calls
- If a class is constructor-injected into the orchestrator of this flow but appears nowhere in the diagram, flag it. Either the diagram is incomplete OR the dependency is dead.

### 7. Transactional model integrity
- If the contract says the flow has an atomic tx (e.g. `OnboardingService.complete`), the diagram must show the tx scope (a `rect` or note marking what's inside `engine.begin()`).
- Flag missing tx visualisation.

### 8. Idempotency / replay paths
- If the contract describes idempotency-key replay, the diagram must show the `alt replay hit / else fresh request` branch.
- Flag if the diagram only shows the happy path.

### 9. Auth + touch_last_seen pattern
- For every authed endpoint flow, the diagram must show `authenticate` + (if applicable) `touch_last_seen`.
- Exceptions: logout + account deletion explicitly skip `touch_last_seen` — note must mention why.
- Flag missing auth steps or missing exception annotations.

## Output

Return findings strictly in the format from `audits/_format.md`.
