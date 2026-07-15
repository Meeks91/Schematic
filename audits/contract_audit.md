# Contract Audit (Phase 4 — Contracts + Models + Function ACs + Tests)

Quality gate for Phase 4. Read the freshly-locked component contract files from this gate and run them through the rules below. Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/components/<class>.md` (one or more — the gate's locked contracts)
- `<schematic_dir>/objective.md` (Feature AC traceability) + `<schematic_dir>/components/_overview.md` §Component Summary (Class AC cross-ref)
- The resolved `styling.<language>` + `testing` standards modules (see `../standards_resolution.md`; defaults: `~/.claude/skills/python-standards/SKILL.md`, `~/.claude/skills/writing-tests/SKILL.md`)
- `<skill_dir>/phase_4_contracts_and_tests.md` (Contract Card Format, Function AC Definition) + `<skill_dir>/SKILL.md` §AC Hierarchy

## Checks (in order)

### 1. Function AC completeness
Each public method MUST have a Function AC with:
- **Functionality** — what inputs/outputs/transformations/invariants
- **Failure modes** — present unless N/A (then omit, not blank)
- **Performance** — present only when constraints exist (omit otherwise)

Flag any public method missing a Function AC.
Flag any Function AC with empty `Functionality:` or copy-pasted boilerplate.

### 2. Signature rigor
- All param types fully specified — no bare `Any`.
- Return types declared explicitly — no implicit `None` returns where a value flows.
- Flag any default parameter values (styling standards: "NEVER default parameters — force callers to be explicit"). The ONLY exception: `conn: sa.Connection | None = None` for the transactional pass-through pattern.

### 3. Optional / Nullable return — flagged for sign-off
Per the styling standards' "Optional fields on a dataclass are a smell" and the skill's Rules section: ANY `X | None` return type or model field MUST have an inline justification (one sentence). Flag any unjustified Optional.

### 4. Swallowed exceptions — flagged for sign-off
Any Function AC that mentions:
- "returns empty …"
- "no-op if …"
- "silent fallback"
- "best-effort"
- "logged, not raised"

MUST be flagged in the contract with `⚠️ USER SIGN-OFF REQUIRED` per the skill's Rules. Flag any swallowed exception without the sign-off marker.

### 5. AC Test naming + coverage
- Test names follow `test_<scenario>` (underscore-separated, lowercase; scenario = the event under test + qualifying `when_<condition>` clause, e.g. `test_successful_submission`, `test_submission_when_slot_limit_reached`; the event is omitted only when the test class scopes to exactly it; numbered suffixes banned). Flag CamelCase, mechanism-chain names (`X_then_Y`), outcome-slice fragmentation, or vague names.
- Every Function AC has ≥1 AC Test. Flag uncovered ACs.
- Each test name is unambiguous about outcome AND condition. Flag "test_works" or similar.

### 6. Model location
- Public models live in `models.py` next to the consuming class.
- Private types prefixed `_` may nest inside the class file.
- Flag inline models that should be in `models.py`.

### 7. Naming intent (role, not shape)
- Constructor params: name the intent, not the slot. `max_workers` → `max_concurrent_seeds`. Flag mechanism-named params.
- Method names: describe outcome, not mechanism. `process()` / `run()` / `call_once()` → name the verb-of-outcome. Flag vague verbs.
- Dict types: ALWAYS `key_to_value: dict[K, V]`. Flag any dict variable named without this pattern.

### 8. Banned patterns
- Magic literals in tests (look for fixture constants `_NAME` style). Flag inline literals in test code.
- `try/except` blocks with broad catches — flag unless the contract explicitly justifies.
- Comments explaining WHAT — flag, only WHY is acceptable.

### 9. Cross-reference integrity
- Constructor deps match the topology in `components/_overview.md` §Component Summary.
- Type names match models defined in `<class>.md` or imported from another `components/*.md`. Flag dangling type refs.

## Output

Return findings strictly in the format from `audits/_format.md`.
