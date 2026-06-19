# Test Naming + Structure Reference

For full test-writing standards (Given/When/Then, fixtures, factory naming, object equality), see `~/.claude/skills/writing-tests/SKILL.md`.

## Test name format (Phase 4 binding)

Pattern: `test_<outcome>_when/for/on_<condition>`

- Lowercase, underscore-separated.
- `<outcome>` describes the asserted user/domain result (verb phrase) — not the refactor mechanism, collaborator, or model source; the test class/file already says what's under test.
- `<condition>` names the precise input/state that triggers it — omit only when the behaviour is unconditional.
- The name reads as a sentence: "test outcome when condition."

### Good

- `test_creates_user_and_issues_session`
- `test_raises_token_expired_when_past_ttl`
- `test_feed_page_preserves_ranked_feed_response`

### Bad

- `test_login` — no outcome, just the method name.
- `test_feed_page_returns_ranked_reels_from_standard_timelines` — names the refactor mechanism instead of the behaviour.
- `test_LoginFlow` — CamelCase; not Python convention.
- `test_does_things` — vague outcome.

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
