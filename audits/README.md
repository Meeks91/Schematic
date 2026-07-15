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

## Blind-spot passes (distinct from conformance audits)

Two **blind-spot passes** ride the P1 and P6 dispatches — a SEPARATE agent hunting **unknown knowns** (blast radius, missed consumers, integration points) rather than rule violations. They are NOT conformance audits: **advisory not gating**, evidence-gated candidates the user dispositions at the phase sign-off, **stateless** (no `schematic phase audit` record). Full spec — charter, output contract, disposition: `audits/_blind_spot_discovery.md`.

## Dispatch protocol (binding for the schematic skill)

At each gate-end, BEFORE printing the `Confirm: y/comment` sigil:

1. Write all this-gate artifacts to disk. **For live-editable artifacts (P5/P6 diagrams): the user's editor review comes FIRST — dispatch the audit (and any blind-spot pass) only on the final, user-reviewed artifact, never on a pre-review draft.**
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
   Before dispatch, substitute every `<schematic_dir>` and `<skill_dir>` placeholder in the
   prompt with the concrete absolute paths (the skill dir is this file's grandparent).
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
3. Reference it from the relevant `phase_N_*.md` file's audit-hook section (and the audit table above).
4. Use the format of an existing audit as a template.
