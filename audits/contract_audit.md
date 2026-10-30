# Contract Audit (Phase 4 — Contracts + Models + Function ACs + Tests)

Quality gate for Phase 4. Its job is the gaps a builder would otherwise find mid-build: a type nobody defines, a value nobody specified, a table or route nobody designed. Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/components/<class>.md` (every locked card) + `<schematic_dir>/components/_overview.md` (§Component Summary, §Storage, §Wire Rules)
- `<schematic_dir>/objective.md` (Feature ACs; § Architecture Deviations)
- The resolved `styling.<language>` + `testing` standards modules (see `../standards_resolution.md`), and `sql-standards` when any card is a Repository
- `<skill_dir>/phase_4_contracts_and_tests.md` (Contract Card Format)

Standards the cards lock (signatures, defaults, `Optional`, model placement, naming, test names) are judged against those modules, citing the rule — never restated here. Code-level patterns (magic literals, try/except, comments) belong to the Phase 8 review, not this audit.

## Checks (in order)

### 1. Type ownership (mechanical)
Run `schematic package check --all --schematic <name>`. Every `MISSING` line is a BLOCKER: a signature or field type defined on no card and absent from src. (Ownership ORDER needs tasks; the post-Phase-7 audit judges it.)

### 2. Open values
Every wire shape, cap, limit, error code, enum spelling and prompt rendering a card leaves unspecified is a BLOCKER — it is ruled into the card before lock, never discovered by a builder. "TBD", "a sensible default" and "as needed" are open values.

### 3. Table sections (Repository cards)
`phase complete 4` already refuses a Repository card with no `**Table**` section; this check reads its content against card item 11 and `sql-standards` § Schema design. BLOCKER: a table named for something other than one row; a second writing repository not listed under Architecture Deviations; a nullable column without its reason; an index or `CHECK` with no access pattern; no `ON DELETE`, retention, migration file or readers.

### 4. Access patterns (Router cards)
Each route answers every question of card item 12; a mutating reply that does not return the revision is a BLOCKER. Enum spelling, casing and id types are cited from `_overview.md` § Wire Rules — a card restating them is a NIT, one contradicting them a BLOCKER.

### 5. Function ACs and loud failure
Every public method has a `Behaviour` line and a `Failure modes` line. A swallowed / empty-return / silent-fallback path, or an `X | None` return or field without its one-line justification and `⚠️ USER SIGN-OFF REQUIRED`, is a BLOCKER.

### 6. Coverage and cross-references
- Every Function AC has ≥1 test (`schematic validate` covers the Feature-AC links).
- Constructor deps match `components/_overview.md` §Component Summary.

### 7. Design quality
The architecture the contracts imply conforms to the architecture standards and is high quality. Real issues or simplifications are flagged.

## Output

Return findings strictly in the format from `audits/_format.md`.
