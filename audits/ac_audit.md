# AC Audit (Phase 1 — Feature Change List + Feature ACs)

You are a quality gate for the schematic skill. Read the freshly-locked Phase 1 artifacts and check them against the rules below. Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/objective.md` (Context & Objective, Functional ACs — the Feature Change List)
- The resolved `styling` standards module for naming (see `../standards_resolution.md`), plus the project's CLAUDE.md
- `<skill_dir>/phase_1_objective_and_acs.md` (the Phase 1 rules being audited against)

## Checks (in order)

### 1. Change-set header present and concise
- Max 2 lines.
- Describes the umbrella work in a casual one-breath sentence — NOT a list of features.
- Flag if it reads as a feature list.

### 2. Every feature is class-anchored
- Each numbered feature names the `Class:` it touches.
- Orphan features (no `Class:` line) are forbidden.

### 3. Each sub-change row has Title / What / Why — all three columns populated
- The Feature Change List is a table per feature (`AC | Title | What | Why`); every row has all columns filled, none empty or copy-pasted.
- `Why` references Feature/Context/Objective — not generic.
- Flag any row where `Why` is restating `What` in different words.

### 4. No Phase 4 leakage in Feature ACs
- Method names, return types, signatures, URL paths, HTTP verbs, status codes, error class names, model field names are **forbidden** at Phase 1.
- Phase 1 captures intent + outcome, not contract.
- Flag any leakage with the specific offending phrase.

### 5. No banned vague verbs
- Banned: `handle`, `process`, `manage`, `system`, `mechanism`.
- Acceptable replacements: name the actual outcome (e.g. "validates" / "persists" / "rejects").

### 6. Feature granularity sanity check
- If a single feature has >5 sub-changes, flag as "likely two features stuffed into one — consider splitting."
- If two features share a class AND have overlapping sub-change titles, flag as "likely duplicated — consider merging."

### 7. Plain-English density
- Information density should be high (precise verbs, named outcomes).
- Bullet voice consistent (imperative + outcome).

## Output

Return findings strictly in the format from `audits/_format.md`.
