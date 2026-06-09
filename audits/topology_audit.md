# Topology Audit (Phase 2 — Class Topology + Class ACs)

Quality gate for Phase 2. Read the freshly-locked classes from this gate (and the cumulative topology so far) and run them through the rules below. Return findings in the format defined in `audits/README.md`.

## Files to read

- `<schematic_dir>/objective.md` §2 (Topology — the locked-so-far class blocks)
- `<schematic_dir>/components/*.md` (if any exist — for cross-reference orphan checks)
- The resolved `types` + `architecture` standards modules (see `../standards_resolution.md`; defaults: `~/.claude/skills/component-types/SKILL.md`, `~/.claude/skills/architecture-standards/SKILL.md`; bundled fallback: `../reference/component_types.md`)
- `/Users/micahsimmons/.claude/skills/schematic/SKILL.md` (Phase 2 + Architecture Principles + Component Types)

## Checks (in order)

### 1. Class suffix vocabulary
For every class in the gate, the suffix MUST be from the resolved component-types vocabulary:
- Allowed: `Service`, `PipelineService`, `RequestPipelineService`, `Controller`, `Router`, `Factory`, `Repository` (or `Repo`), `Validator`, `Resolver`, `Client`, `Manager`, `<Noun><Verb>er` (e.g. `Ranker`, `Parser`).
- **Banned: `Loader`, `Reader`, `Writer`, `Helper`, `Handler`.**
- Flag every banned suffix with the offending class name and propose a vocabulary-compliant alternative (often `Resolver` for what's labelled `Loader`).
- Flag stacked suffixes (e.g. `RetrieverClient` = Verb-er + Client). One suffix only.

### 2. Service Classification Gate (the gate that was missing — apply rigorously)
For each class classified as INTERNAL (anything not `Service`/`PipelineService`/etc.) ask:
- **Coherent domain test:** does this class own a nameable capability domain on its own (idempotency, taxonomy, scheduling, notifications, OAuth verification, …)?
- **Cross-consumer test:** does any other Service in the cumulative topology need this class directly? Count `Necessitated by:` Feature-AC refs — ≥2 distinct Feature ACs is a strong signal.

Flag any class that answers Yes to either question but is NOT classified as `Service` (or `Repository` if its concern is purely data access). Suggest the promotion + new top-level folder name.

### 3. Class AC purity (no Phase 4 leakage)
Class ACs MUST NOT name:
- Method names, parameter names, return types
- URL paths, HTTP verbs, status codes
- Model field names, exception class names
- Header names, body shapes

Replace with the concern represented. Flag every leak.

### 4. Conjunction-joined responsibilities (=split-class smell)
Flag any Responsibility bullet joining unrelated concerns with `AND`. Example: "Owns persistence AND validation AND billing state" → split.

### 5. Missing `Never:` bullets
Where scope creep is plausible (e.g. a Repository class that could plausibly grow to own sessions), flag absence of a `Never:` bullet pinning what the class does NOT own.

### 6. Necessitated-by bullets are dependency-named AND direct-necessity only
Each `- N.X — <reason>` bullet MUST name *why the feature needs this class* (the dependency), not what the class does. 5–10 words. Flag bullets that restate Responsibility.

**Direct-necessity rule (binding — do NOT violate by flagging "missing" transitive refs):** A Feature AC belongs under `Necessitated by` ONLY if it forces a code change in THIS class. **Do NOT flag a class for "missing" an AC whose code change lives in a different class, even if THIS class is on the runtime chain.** Transitive chaining is explicitly forbidden — it would make every class list every AC.

Worked example of what NOT to flag:
- AC `2.C — persisted payload carries a make-it-yours entry` lives on the Repository (serializer change). The Service that calls `.persist()` and the Factory that returns the domain object do NOT need `2.C` in their `Necessitated by`, even though the data flows through them. If you find yourself thinking "but the class is on the chain that makes the AC observable" — that's transitive-necessity, which the rule rejects. The Service is necessitated by the AC that drove ITS code change (e.g. `2.A — wire the new analyser`); the Factory is necessitated by the AC that drove ITS code change (e.g. `2.B — first-class domain field`).

### 7. Orphan / dangling-reference check (cross-gate)
- Any class referenced in another component file's Constructor or Public API but NOT in the topology summary? Flag as orphan.
- Any class in the topology but NOT referenced by any other component? Flag as potentially unnecessary.

### 8. Banned class names (project-specific)
- `<Anything>Loader`, `<Anything>Helper`, `<Anything>Handler` → flag with suggested vocabulary-compliant rename.

## Output

Return findings strictly in the format from `audits/_format.md`.
