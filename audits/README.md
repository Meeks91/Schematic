# Audit Hooks

Audit hooks are background Sonnet agents dispatched at gate-end checkpoints. Their job is to catch violations of the resolved standards modules (see `../standards_resolution.md`; project CLAUDE.md as legacy fallback) and the schematic skill's rules **before** the user locks the gate — when corrections are still cheap.

> **Every audit prompt MUST instruct the agent to read these two shared files first:**
> - `_precedence.md` — DO NOT FLAG list (confirmed non-issues)
> - `_format.md` — output schema, severity gates, and hard caps
>
> Both files are mandatory inputs for every audit dispatch. The skill's dispatch protocol below references them by name; the per-audit prompts (`ac_audit.md`, `topology_audit.md`, etc.) inherit their rules.

## When audits run

Audits fire **once per phase, at phase completion** — the final sub-gate that closes the phase. Earlier sub-gates within a phase (e.g. each ≤3-class batch in Phase 2 or 4) do NOT trigger an audit; they only gate user content sign-off on that batch.

| Audit | Phase | When |
|---|---|---|
| `ac_audit.md` | 1 | After Feature Change List + Feature ACs are drafted, before locking the phase |
| `topology_audit.md` | 2 | After ALL topology gates have been content-signed-off, before locking the phase |
| `contract_audit.md` | 4 | After ALL contract gates have been content-signed-off, before locking the phase |
| `sequence_audit.md` | 6 | After ALL sequence gates have been content-signed-off, before locking the phase |
| `end_to_end_audit.md` | 7 | After all Phase 7 tasks are drafted, before final lock |

Phase 3 (Directory Structure) and Phase 5 (DAG + App Integration) do not have dedicated audits — they are mechanical artifacts derived from Phase 2 + 4 + 6, and any drift there is caught by the topology / contract / sequence audits.

## Dispatch protocol (binding for the schematic skill)

At each gate-end, BEFORE printing the `Confirm: y/comment` sigil:

1. Write all this-gate artifacts to disk.
2. Dispatch the audit:
   ```
   Agent({
     description: "<phase> audit",
     subagent_type: "general-purpose",
     model: "sonnet",
     run_in_background: true,
     prompt: <contents of audits/<phase>_audit.md> + "Files to read: <concrete paths>"
   })
   ```
3. Present the artifact summary to the user.
4. When the audit returns:
   - **Clean** → print `✓ Audit (<phase>): clean` above the Confirm sigil.
   - **Findings** → print `⚠️ Audit (<phase>) flagged:` followed by the bulleted list. User decides whether to address before locking or accept and proceed.
5. **NEVER lock without the audit having returned.** If parallel run hasn't completed by the time you'd print the sigil, wait.

## Output contract (every audit MUST follow)

See `audits/_format.md` for the exact output schema, severity gate questions, and hard caps. In brief:
- **Clean:** `✓ Clean` — nothing else (end-to-end audit appends a count tally).
- **Findings:** structured `F<n>: SEVERITY | file:section | finding | rationale` lines, ≤8 total.

## Why parallel

Audits run in the background while the planner-agent presents the gate summary to the user. Wall-clock cost is usually zero — by the time the user has read the summary, the audit has returned. The audit gates the `Confirm: y/comment` sigil, not the artifact write.

## Adding a new audit

1. Drop a new `<name>_audit.md` in this directory.
2. The file must be self-contained: any context the agent needs goes in the prompt.
3. Reference it from the relevant phase block in `SKILL.md` at the dispatch point.
4. Use the format of an existing audit as a template.
