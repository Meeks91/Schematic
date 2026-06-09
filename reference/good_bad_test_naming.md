# Test Naming + Structure Reference

For full test-writing standards (Given/When/Then, fixtures, factory naming, object equality), see `~/.claude/skills/writing-tests/SKILL.md`.

## Test name format (Phase 4 binding)

Pattern: `test_<method>_<outcome>_when/for/on_<condition>`

- Lowercase, underscore-separated.
- `<method>` is the public method under test (the prefix), so tests group by method.
- `<outcome>` describes the asserted result (verb phrase).
- `<condition>` names the precise input/state that triggers it — omit only when the behaviour is unconditional.
- The name reads as a sentence: "test method outcome when condition."

### Good

- `test_login_creates_user_and_issues_session`
- `test_authenticate_raises_token_expired_when_past_ttl`
- `test_update_settings_rolls_back_on_settings_update_failure`

### Bad

- `test_login` — no scenario, no outcome.
- `test_user_repository_works` — vague, untestable.
- `test_LoginFlow` — CamelCase; not Python convention.
- `test_authenticate_does_things` — vague outcome.

## Test pairing rule

Every Function AC MUST have at least one AC Test. Naming should make the linkage obvious:

```
Function ACs:
  AC-4.5.2  authenticate — validate a bearer token (pure read)

AC Tests:
  - test_authenticate_returns_session_for_valid_token         — proves AC-4.5.2 happy path
  - test_authenticate_raises_token_unknown_when_missing       — proves AC-4.5.2 failure mode
  - test_authenticate_raises_token_revoked_when_revoked       — proves AC-4.5.2 failure mode
  - test_authenticate_raises_token_expired_when_past_ttl      — proves AC-4.5.2 boundary
  - test_authenticate_does_not_mutate_session_row             — proves AC-4.5.2 pure-read invariant
```

The trailing `— proves AC-N.X` comment is optional but useful for traceability.

## Branch tests

For internal branches not directly covered by an AC (e.g. boundary conditions, parameterized variants), use the same naming pattern. Listed separately under `## Branch Tests` in the contract block.

## Python test layout

See the canonical Python test example in `~/.claude/CLAUDE.md` (search for "Python Test Example") — covers fixtures, `_gen_*` factory helpers, G/W/T comments, object-equality assertions, and cascading style inside test bodies.
