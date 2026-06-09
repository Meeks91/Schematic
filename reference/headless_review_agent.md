# Headless Review Agent — Design Notes

## How it works today

When `schematic task status <tag> review` is run, the CLI:
1. Writes a `review_request` to `.schematic-state.json` (with tag, target, component_file metadata)
2. Spawns `claude -p "<prompt>"` as a background process
3. The agent reviews the code, leaves notes via `schematic task note`, and optionally marks complete

## Claude Code headless/bare modes

### `-p` mode (current approach)
- Runs a single prompt, outputs to stdout, exits
- No interactive follow-up — fire and forget
- Agent runs with standard permission prompts (user must pre-allow relevant tools)
- Best for: single-pass review where findings are written back via CLI

### Headless daemon (future consideration)
- `claude --headless` could run as a long-lived process watching for review requests
- Poll `.schematic-state.json` for `review_request.status === "pending"`
- Process each, mark as "reviewed", leave notes
- Pro: no per-invocation cold start, can batch reviews
- Con: resource cost of idle daemon, complexity of lifecycle management

### Sub-agent via MCP (alternative)
- If claude code exposes an MCP tool for spawning sub-agents, the main session could dispatch reviews inline
- The schematic skill's watcher pattern (bridge.py foreground mode) already does this for Q&A
- Pro: integrated into the conversation, agent answers are immediate
- Con: blocks the main agent while reviewing

## Recommended approach

**Use `claude -p` for automated reviews.**

Rationale:
- Zero infrastructure — just a CLI invocation
- The review agent is ephemeral: spawn, review, write notes, exit
- Notes persist in state JSON, visible in dashboard
- No daemon lifecycle to manage
- If `claude` is not on PATH, fallback to printing the review prompt for manual execution

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
