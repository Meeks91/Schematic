# Phase 9: Compression

Runs after the user signs off Phase 8 implementation. Mandatory — not skippable.
The user's sign-off on implementation is the trigger; compression itself has no gate.

## Purpose

Compress the schematic's knowledge into the repo's persistent knowledge base,
then clean up. The schematic was the planning artifact; the repo's arch docs
are the long-term record. This phase bridges one to the other.

## Input

- Completed schematic bundle at `docs/schematics/<feature>/`
- `completionCompression` config from `standards.json` (configured at init)

## Execution

```
1. Read strategy from standards.json → schematic.completionCompression.strategy
2. Read archDocsPath from config
3. Execute the integration instructions in the strategy:
   a. Sequence integration
   b. Business logic / decision integration
4. Record completion: `schematic phase complete --schematic <name> 9`
   (BEFORE cleanup — the state file lives inside the schematic dir)
5. Cleanup: delete or preserve the schematic dir per config. Deletion is
   destructive — propose the exact `rm -rf` command for the user to run,
   or use the IDE/tooling delete the user has sanctioned.
```

## Default strategy (reference — what gets written if user accepts defaults)

```
On schematic completion:
  1. Sequence diagram: if an existing architecture sequence diagram exists
     at <archDocsPath>, integrate the schematic's sequence into it (merge
     participants and flows). If no existing sequence exists, create a new
     feature sequence doc at <archDocsPath>/<feature>.mmd.
  2. Business logic & decisions: integrate the core summary (from
     objective.md) and decision log into existing feature documentation.
     If no existing docs exist, create <archDocsPath>/<feature>.md
     containing the objective, core summary, decision log, and a
     reference to the sequence diagram.
  3. Schematic dir: delete docs/schematics/<feature>/ in full.
```

## What gets integrated (default)

| Source (schematic) | Target (repo docs) | Mode |
|---|---|---|
| `sequence.mmd` | Existing arch sequence OR new `<archDocsPath>/<feature>.mmd` | Merge if exists, create if not |
| `objective.md` → Core Summary | `<archDocsPath>/<feature>.md` | Section in feature doc |
| `objective.md` → Decision Log | `<archDocsPath>/<feature>.md` | Section in feature doc |
| `objective.md` → Purpose | `<archDocsPath>/<feature>.md` | Header in feature doc |
| `dag.mmd` | NOT integrated | Dies with schematic dir |
| `components/*.md` | NOT integrated | Dies with schematic dir |
| `tasks.md` | NOT integrated | Dies with schematic dir |
| `research/` | NOT integrated | Dies with schematic dir |

## Binding rules

- **No re-asking.** The strategy was configured at init. Execute it.
- **Idempotent.** If interrupted and re-run, same result.
- **Verify before deleting.** Confirm integration targets exist on disk before deleting schematic dir.
- **Commit separately.** Own commit: `chore: compress <feature> schematic into arch docs`.

## CLI gate

```
schematic phase complete --schematic <name> 9
```

No audit hook — mechanical execution, not design judgment.
No user gate — strategy was pre-approved at init.

## Completion output

One message, no gate:

```
── COMPRESSION COMPLETE ──────────────────────────────────────────
Integrated into: <archDocsPath>/<files written>
Deleted:         docs/schematics/<feature>/
Strategy used:   <first line of strategy text>
──────────────────────────────────────────────────────────────────
```
