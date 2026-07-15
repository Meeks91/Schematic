# Test Naming + Structure Reference

For full test-writing standards (Given/When/Then, fixtures, factory naming, object equality), see `~/.claude/skills/writing-tests/SKILL.md`.

## Test name format (Phase 4 binding)

Pattern: `test_<scenario>` — the scenario is the event under test plus its qualifying state

- Lowercase, underscore-separated.
- A feature test asserts the scenario's FULL contract in one test — return shape AND every state mutation — so the name never enumerates individual outcomes.
- Include the event unless the enclosing class already scopes to exactly it (no redundant prefixes).
- Two scenarios of the same event differ by their `when_<condition>` clause — numbered suffixes (`_1`, `_2`) are banned.
- Omit the condition only when behaviour is unconditional.

### Good

- `test_successful_submission`
- `test_submission_when_slot_limit_reached`
- `test_raises_token_expired_when_past_ttl` — class scopes the event; the raise IS the scenario.

### Bad

- `test_compute_1` — a numeral is not a scenario.
- `test_works` / `test_empty` — no event.
- `test_post_authenticates_then_adds_entry` — mechanism chain; internal steps are not the scenario.
- `test_submit_returns_subscription` — outcome slice; the scenario's full contract belongs in ONE test.
- `test_LoginFlow` — CamelCase; not Python convention.

Existing test names in the repo do NOT override this standard — never copy a live naming idiom that conflicts with it.

## Test pairing rule

Every Function AC MUST have at least one AC Test. Naming should make the linkage obvious:

```
Function ACs:
  AC-4.5.2  authenticate — validate a bearer token (pure read)

AC Tests:
  - test_returns_session_for_valid_token         — proves AC-4.5.2 happy path
  - test_raises_token_unknown_when_missing       — proves AC-4.5.2 failure mode
  - test_raises_token_revoked_when_revoked       — proves AC-4.5.2 failure mode
  - test_raises_token_expired_when_past_ttl      — proves AC-4.5.2 boundary
  - test_does_not_mutate_session_row             — proves AC-4.5.2 pure-read invariant
```

The trailing `— proves AC-N.X` comment is optional but useful for traceability.

## Branch tests

For internal branches not directly covered by an AC (e.g. boundary conditions, parameterized variants), use the same naming pattern. Listed separately under `## Branch Tests` in the contract block.

## Python test layout

See the canonical Test Styling Example in the resolved Python styling module (default: `~/.claude/skills/python-standards/SKILL.md`) — covers fixtures, `_gen_*` factory helpers, G/W/T comments, object-equality assertions, and cascading style inside test bodies.
