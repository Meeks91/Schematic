# Phase 4: Contracts + Models + Function ACs + Tests

> **CLI gate commands:**
> - `schematic phase audit --schematic <name> 4 "clean" | "<findings>"` — after contract audit returns, before the Confirm sigil.
> - `schematic phase sign-off --schematic <name> 4` — on user `y`.
> - `schematic phase complete --schematic <name> 4` — immediately after sign-off.

The goal of this phase is to define **what each method must achieve** — producing Function ACs, models, and the tests that prove them.

Writes to `<schematic_dir>/components/<class>.md` (one per class) and, at phase-end, `<schematic_dir>/components/_overview.md` (AC Traceability Matrix).

## Per-class lock order (single atomic gate per class, do NOT split)

1. **Method signatures** — full types, parameters, return types (the API table)
2. **Models / Config** — the shapes that appear in signatures
3. **Behaviour** — the one-line per-method behaviour + any `Behaviour notes` (failure modes, invariants)
4. **Feature tests** — one per behaviour/AC; binding, sign-off required
5. **Branch tests** — anticipated internal paths; extensible during implementation

All sub-blocks appear together in one card per class. One `Confirm: y/comment` locks the whole card. On `y`, write to `components/<class_name>.md` before moving to the next class.

Present max 3 classes per gate.

---

## Function AC Definition (the content behind the card)

Each public method must define what it achieves. In the card format below this maps to:

- **Functionality** → the `Behaviour` column (one line) + the method's Feature tests.
- **Failure modes** → a `**Behaviour notes**` bullet beneath the API table (invalid input, missing data, upstream failure, propagation). Only when applicable.
- **Performance** → a `**Behaviour notes**` bullet, only when a real constraint exists.

⚠️ Any swallowed/empty/silent-fallback path, optional/nullable field, or `SessionToken`-for-auth in a pipeline MUST be flagged for explicit user sign-off (see `reference/component_types.md` Design Smells).

---

## Contract Card Format (BINDING — every class)

Each class is ONE card in `components/<class_name>.md`. The same layout renders in chat and on disk. **Tables are the primary idiom** — they scan cold and stay scannable across many cards. For a Modified class, show **only what changes** — never include "unchanged" rows.

Fixed order:

1. **Heading** — an `H2` that is the class name in backticks: `## \`ClassName\``. One card = one class; the heading IS that class. NEVER a prose sentence, NEVER "Card N — ClassName — MODIFIED".
2. **Identity line** — `**Dir:** \`path\` · **Type:** New | Modified`
3. **Change Required** — a `**Change Required**` bold heading then a bullet list, **max 2 lines, fewer is better**. What the change is / why the class exists.
4. **Constructor changes** — *(only if new or changed deps)* a bold heading `**Constructor changes**` then a table: `Dependency | Type | Role`. Contains ONLY constructor dependencies — never methods.
5. **New methods** — *(only methods that did not exist before)* a bold heading `**New methods**` then a table: `Name | Parameters | Returns | Behaviour` (`Behaviour` one line). Routes use `Name | Route | Returns | Behaviour`.
6. **Updated methods** — *(only methods whose signature or behaviour changed)* a bold heading `**Updated methods**` then a table: `Name | Change`. `Change` is a **one-line max** explanation of what changed (e.g. `user_id → user; drops find_by_id`). Do NOT re-spec the full signature — only the delta.
7. **Behaviour notes** — *(only if needed)* short bullets for failure modes, invariants, atomicity, ordering. This is where detail lives — keep it OUT of the table cells.
8. **Models / Config** — *(only if any)* a table per shape, with the model/file named above it: `Field | Type | Note` (models) or `Key | Value | Note` (config).
9. **Errors** — *(only if the class raises domain errors)* table: `Code | Meaning`.
10. **Tests** — ALWAYS two tables (never an inline `·`-separated list): **Feature tests** then **Branch tests**, each with columns `Test | Proves`. If a behaviour is already covered by an existing unchanged test, do NOT repeat it — note the coverage in one line.

Rules:
- **Separator between cards (when a gate shows >1 card):** put a long red rule between consecutive cards — a `diff` fenced block containing a single `-`-prefixed line of ~95 dashes (renderers colour `-` lines red, giving a strong section break). NOT a bare `---` (too short, renders grey). Example:
  ````
  ```diff
  -----------------------------------------------------------------------------------------------
  ```
  ````
- Every section after the identity line gets its own **bold heading** — Constructor changes, New methods, Updated methods, etc. Nothing renders bare under the previous table (that makes methods look nested under the constructor).
- A **New** class lists all its methods under **New methods**; it has no **Updated methods** section.
- A **Modified** class splits: genuinely new methods → **New methods** (full signature); changed methods → **Updated methods** (1-line delta only). Unchanged methods appear NOWHERE.
- Names, params, types, fields, paths, codes → backticks everywhere the eye should snap to a token.
- New-method signatures live in the New-methods table (`name` · `param: Type` · `Return`), NOT in prose or code fences. Use a code fence ONLY for a multi-line snippet a table genuinely cannot express.
- No "unchanged" rows. No stray `return` row — the return type is the `Returns` column.
- `Change Required` is hard-capped at 2 bullet lines.

### Worked reference

```
## `OnboardingService`
**Dir:** `src/services/api/userOnboarding/OnboardingService.py` · **Type:** Modified

**Change Required**
- Promote the user off `UNREGISTERED` onto the config registration tier in the existing tx.
- Take the resolved `User` instead of `user_id` (no re-load).

**Constructor changes**
| Dependency | Type | Role |
|---|---|---|
| `options_provider` | `UserOptionsProviderService` | source the configured registration tier |

**New methods**
| Name | Parameters | Returns | Behaviour |
|---|---|---|---|
| `promote_to_registered_tier` | `user: User` | `User` | Moves the user off `UNREGISTERED` onto the configured tier |

**Updated methods**
| Name | Change |
|---|---|
| `complete` | `user_id → user`; promotes onto the configured tier in-tx |

Feature tests
| Test | Proves |
|---|---|
| `test_complete_promotes_user_to_default_registered_tier` | promotion happens |
| `test_complete_rolls_back_promotion_when_settings_insert_fails` | atomicity |

Branch tests
| Test | Proves |
|---|---|
| `test_complete_reads_registered_tier_from_options_provider` | config-driven tier |
```

**Function AC examples (content):** see `reference/good_bad_function_ac.md`.

**Test naming + structure examples:** see `reference/good_bad_test_naming.md`.

---

## Tests assert THIS unit, not downstream collaborators

A test belongs in the component file of the unit that OWNS the behaviour.

If a behaviour is enforced by a downstream collaborator (a repo's uniqueness constraint, a validator's
invariant, a parser's normalisation), the test belongs in THAT collaborator's card — not this one.
Mocking the collaborator makes the test either a tautology (mock returns what you told it) or
unreachable (the behaviour lives behind the mock boundary).

This unit's tests prove three things only:

1. **Delegation** — the right call was made.
2. **Response packing** — object-equality on the returned shape.
3. **Exception propagation** — the right typed error bubbles.

Quick check before adding a test: *"if I mocked the collaborator entirely, could this test still
meaningfully fail?"* If no — it belongs in the collaborator's card.

---

## Phase 4 End: AC Traceability Check

After all class contracts are locked, produce the traceability matrix (proving the AC pyramid from
`SKILL.md` is complete). Write to `components/_overview.md`.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AC TRACEABILITY MATRIX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature AC-1: <title>  (objective.md)
  └── Class AC: <ClassName> — <responsibility>  (components/_overview.md component summary)
       └── Behaviour: <method> — <title>  (components/<class>.md)
            └── test_<name>  (components/<class>.md)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Every Feature AC covered: ✓ / ✗
- Every Class AC traces to ≥1 behaviour: ✓ / ✗
- Every behaviour has a Feature test: ✓ / ✗
- Orphan check (components with no Feature AC): <list or "none">
- Tally: N Feature ACs, M Class ACs, P behaviours, Q Feature tests, R Branch tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This references by section/card only — it does NOT restate test names or contract details.

### Audit hook (mandatory — fires once, after traceability matrix is written)

Earlier sub-gates (each ≤3-class batch) do NOT trigger an audit. This fires once when all contract cards are content-signed-off and the traceability matrix is written.

1. Dispatch `audits/contract_audit.md` per `audits/README.md`. Wait for it to return.
2. Surface findings above the sigil.
3. Record: `schematic phase audit --schematic <name> 4 "clean" | "<findings>"`

**Confirm: y/comment**

---

**Next:** `phase_5_injection_dag.md`
