# Audit Output Format (shared across all audits)

Every audit MUST return findings in this structured form. Free-form prose audits are banned — they vary report-to-report and slow review.

## Output schema

```
F<n>: <SEVERITY> | <file>:<section> | <one-line finding> | <one-line rationale>
```

- `<n>` — sequential, starting at F1.
- `<SEVERITY>` — `BLOCKER` | `NIT` | `OBSERVATION` (see `_precedence.md`).
- `<file>` — relative path within the schematic bundle (`components/foo.md`, `objective.md`).
- `<section>` — the H2 / H3 / AC ref where the issue lives (`§Constructor`, `§AC-1.1 Failure modes`).
- `<one-line finding>` — what is wrong (≤ 20 words).
- `<one-line rationale>` — why it matters (≤ 15 words).

## Hard caps

- **≤ 8 findings total.** If more, raise only the top 8 by severity. Aggregate the rest as one `OBSERVATION` line ("N additional nits suppressed").
- **≤ 400 words total output.** Trim rationales before findings.
- **No multi-paragraph findings.** One line per finding. Period.
- **No "audit summary" paragraph.** The findings list IS the report.

## Severity gates (BINDING — apply before emitting any finding)

Before emitting any line, ask the two questions in the column header for that severity. If you cannot answer **yes** to both, do not emit the line.

| Severity      | Q1 — Would it block?                                                | Q2 — Is the cause concrete?                                          |
|---------------|---------------------------------------------------------------------|-----------------------------------------------------------------------|
| `BLOCKER`     | Would shipping with this break the build, the AC pyramid, or a contract invariant? | Can you point to the exact file:section + cite the contradiction? |
| `NIT`         | Would a competent human reviewer also flag this in code review?     | Is the fix a single-line edit with a clear right answer?              |
| `OBSERVATION` | Would the user **change a decision** if they read this?             | Is there a non-cosmetic action item attached?                         |

**Examples by severity:**
- **BLOCKER:** AC pyramid orphan, naming mismatch between files, swallowed exception, missing failure-mode propagation, contract self-contradiction.
- **NIT:** missing exception type in a failure mode, count drift between matrix and components, stale section header text.
- **OBSERVATION:** "production codebase already has X — consider reusing instead of creating Y." Not: phrasing nits, restated-what-we-already-know observations.

**OBSERVATION suppression rule (strict):** If the finding would not change a downstream decision — if the user's response would be "noted, no action" — DROP IT. Borderline test-name clarity nits, stylistic phrasing concerns, and "this could be reworded" notes are NOT OBSERVATIONs. They are noise. Either escalate to NIT with a concrete fix, or omit entirely.

**Default to omission.** When in doubt about whether a finding clears these gates, leave it out. A clean audit on a real issue is more valuable than a noisy audit that buries real issues under trivia.

## Anti-patterns (do NOT emit these)

- **Phrasing nits** — "could be clearer", "risks confusion", "phrasing is awkward". Either propose a concrete rewrite (NIT) or drop.
- **Tautology callouts** — flagging a test as testing the absent state of a dep that doesn't exist. If the design choice is structural (encoded in the contract), it doesn't need a finding.
- **Style-preference findings** — capitalization, ordering of equivalent items, list-vs-table choice. If the skill rules don't mandate one form, it's not a finding.
- **Forward-looking concerns** — "this might be hard to test later", "future maintainers may find this confusing". Audits review present state, not future risk.

## Clean case

If nothing flags, return exactly:
```
✓ Clean
```

Nothing else — except the end-to-end audit (phase 7) which appends a count tally (see `end_to_end_audit.md`).

## Why this format

- Machine-parseable — `schematic phase audit` records the line verbatim.
- Severity-sorted output lets the user fix BLOCKERs first.
- Hard caps prevent the 20-bullet wall that buries real findings under trivia.
- Forced rationale column kills "naked findings" with no justification.
