# Headless Review Agent — Design Notes

## How it works today

When `schematic task status <tag> review` is run, the CLI:
1. Writes a `review_request` to `.schematic-state.json` (with tag, target, component_file metadata)
2. Spawns `claude -p "<prompt>"` as a background process
3. The agent reviews the code and records findings via `schematic task note` (it does not complete the task — completion stays with the implementing agent via `schematic-task-done`)

## Dispatch mode: `claude -p` (chosen)

Single prompt → stdout → exit. Fire-and-forget; agent runs with standard permission prompts (user pre-allows tools); findings written back via CLI.

**Why `-p` over the alternatives:**
- Zero infrastructure — just a CLI invocation; ephemeral agent (spawn, review, write notes, exit).
- Notes persist in state JSON, visible in dashboard.
- If `claude` is not on PATH, fall back to printing the review prompt for manual execution.

Rejected: a long-lived `--headless` daemon (idle resource cost, lifecycle complexity) and MCP sub-agent dispatch (blocks the main session while reviewing).

## Security considerations

- The agent runs with standard permissions (no `--dangerously-skip-permissions`)
- The agent is scoped to the project root (cwd)
- Review prompt constrains the agent to read-only analysis + writing notes
- No network access needed for local code review
- For CI/CD integration, use a dedicated service account token

## Integration with dashboard

The dashboard already shows agent notes on task cards:
1. Review agent runs `schematic task note <tag> "findings..."` 
2. State JSON is updated with the note
3. Dashboard polls `/api/state` and renders notes in the task modal
4. Wave animation on pending review, green checkmark on pass
