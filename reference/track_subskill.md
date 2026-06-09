# schematic track — Feature Flow Tracer

> **Lazy-loaded subskill.** Only read this file when `schematic track` is invoked.

## Purpose

Traces an entire feature/flow end-to-end through the codebase, producing a structured artifact that captures:
- Execution steps (ordered)
- Data sources per step (DB, S3, API, cache)
- Business logic / transformations applied
- Conditions / gates
- Input → output per step

A schematic can have **multiple named traces** — each trace captures a distinct flow through the same feature (e.g. `benchmark-pipeline`, `hedged-flow`).

## CLI Usage

### Init (scaffold a new trace)
```
schematic track init --schematic <name> --entry <file:line|class|route> --trace <trace-name>
```
- `--trace` must be kebab-case (e.g. `benchmark-pipeline`, `hedged-flow`)
- Creates `docs/schematics/<name>/research/traces/<trace-name>/trace.json` with pending status

### Validate
```
# Validate ALL traces for a schematic:
schematic track validate --schematic <name>

# Validate a single trace:
schematic track validate --schematic <name> --trace <trace-name>
```

### Show
```
# Summary of all traces (table view):
schematic track show --schematic <name>

# Detailed steps for a single trace:
schematic track show --schematic <name> --trace <trace-name>
```

## Directory Structure

```
docs/schematics/<name>/research/traces/
├── benchmark-pipeline/
│   ├── trace.json
│   ├── trace.mmd
│   ├── trace.paths.json
│   └── trace.md
├── hedged-flow/
│   ├── trace.json
│   ├── trace.mmd
│   ├── trace.paths.json
│   └── trace.md
└── _index.json   ← registry of all traces
```

## `_index.json` Format

```json
{
  "traces": [
    {"name": "benchmark-pipeline", "entry": "BenchmarkRoute.kt:110", "status": "complete", "steps": 11},
    {"name": "hedged-flow", "entry": "BenchmarkRoute.kt:76", "status": "pending", "steps": 0}
  ]
}
```

Status values: `complete` (has steps) | `pending` (0 steps).

## Backward Compatibility

If an old-style `trace/` directory exists (no `research/traces/`), it is migrated automatically on the next `validate` or `show` call:
- Moves `trace/` → `research/traces/default/`
- Creates `_index.json` with a single "default" entry

## Output Files (per trace)

- `trace.json` — structured step list (machine-readable)
- `trace.mmd` — mermaid flowchart (human-readable)
- `trace.paths.json` — node-to-file mapping for IDE open
- `trace.md` — annotated reference table

## Agent Prompt (what the tracer does)

The tracer agent receives:
1. The entry point (file/class/route)
2. The project root path
3. The schematic name
4. The trace name

It then:
1. Reads the entry point file
2. Follows the execution chain (method calls, route dispatches, processor chains)
3. For each step, records: name, condition, data source, transformation, file path + line
4. Continues until a terminal step (output/stop)
5. Writes all four output files into `traces/<trace-name>/`

## Integration with the Mermaid Editor

After trace completes, the agent can launch the mermaid editor:
```
python3 <skill_dir>/reference/mermaid_edit/bridge.py <schematic_dir>/traces/<trace-name>/trace.mmd
```

The `.paths.json` file enables right-click → Open in IDE on each traced node.

## Mermaid Node Formatting Standard

Every trace box MUST follow this format — no exceptions:

```
ID["<b>step-name</b><br/>* purpose: what this step does (verb phrase)<br/>* in: input type/shape<br/>* out: output type/shape<br/>* verdict: ✓ PASS / ⚡ CHANGE / ✓ SKIP + reason"]
```

**Rules:**

- Single shape for ALL nodes: rectangle `["..."]` — no diamonds, stadiums, or other shapes
- Line 1: `<b>step-name</b>` — bold, exact route/processor name
- Lines 2–5: prefixed with `*` as bullet markers, one concern per line:
  - `* purpose:` — what the step does in ≤8 words (verb phrase)
  - `* in:` — concrete input type (e.g. `List‹Holding›`, `DailyInputMessage`)
  - `* out:` — concrete output type, noting what changed
  - `* verdict:` — FDP assessment with reason
- Use `‹›` for generics (not `<>` — conflicts with HTML)
- Separate each line with `<br/>`
- MAX 5 lines per box (title + 4 bullets)

**Verdict symbols:**

| Symbol | Meaning | Color |
|---|---|---|
| ✓ PASS | No changes needed, works as-is | Green `#4CAF50` |
| ✓ SKIP | Step not invoked for this source | Green `#4CAF50` |
| ⚡ CHANGE | Code change required | Orange `#FF9800` |
| ⚡ NEW | Entirely new step to build | Orange `#FF9800` |
| ■ OUTPUT | Terminal/sink step | Blue `#2196F3` |

**Edge labels:**

- Only label edges that have a real condition (e.g. `-->|"isHedged=true"|`)
- Omit labels on unconditional edges (just `-->`)
- Condition text must be the actual code predicate or flag value

**Example (correct):**

```mermaid
A["<b>retrieve-benchmark-returns</b><br/>* purpose: POST to Trundl, map response to holdings<br/>* in: DailyInputMessage<br/>* out: List‹Holding›<br/>* ⚡ NEW: add fdp_index_position branch"]
```

**Anti-patterns (banned):**

- Type badges (`<i>entry</i>`, `<i>processor</i>`) — noise, doesn't help reading
- "unconditional" / "always" labels — if there's no condition, don't say so
- Fancy shapes for "type" differentiation — shapes don't aid comprehension
- `<br/>` line dumps without bullet markers — unreadable wall of text

## Step Schema

```json
{
  "steps": [
    {
      "id": "A",
      "name": "POST /local-ingest",
      "type": "entry|processor|enrichment|predicate|output",
      "condition": null | "isHedged == true",
      "dataSources": ["DB: common.security", "S3: benchmark/"],
      "transformation": "unmarshal JSON → DailyInputMessage",
      "input": "HTTP POST body (JSON)",
      "output": "DailyInputMessage exchange property",
      "file": "src/main/.../MainRoute.kt:130",
      "next": ["B"],
      "nextConditions": {"B": null}
    }
  ]
}
```
