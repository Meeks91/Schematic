# Phase 0 — Standards Resolution

Runs at `schematic init`, before Phase 1. If no manifest is resolved by the time any later phase starts, STOP and run this first.

## Purpose

Schematic absorbs the conventions of the repo it runs in. Standards are **pluggable per-slot** — a repo maps each slot to a standards module; anything unmapped is **learned from the codebase**. Once resolved, every phase reads and QUOTES from the resolved modules instead of assuming any one CLAUDE.md layout.

## Slots

| Slot | Governs | Consumed by |
|---|---|---|
| `architecture` | service layout, directories, models placement, DI, boundaries | P2, P3, P5 |
| `types` | class-suffix / component-type vocabulary, banned suffixes | P2, topology + contract audits |
| `styling.<language>` | naming, formatting, idioms, defensive-code policy | P4, P8 |
| `testing` | test planning, naming, G/W/T, object-equality | P4, P7, P8 |
| `exemplars` | known-good dirs to imitate | learn mode, P8 |

## Manifest

`.claude/standards.json` at the repo root. User-global default: `~/.claude/standards.json` (repo manifest overrides it).

```json
{
  "architecture": "skill:architecture-standards",
  "types": "skill:component-types",
  "styling": {
    "python": "skill:python-standards",
    "typescript": "skill:typescript-standards"
  },
  "testing": "skill:writing-tests",
  "exemplars": ["src/services/reelEnrichment/"],
  "unresolved": "learn"
}
```

**Source kinds:**

| Kind | Resolves to |
|---|---|
| `skill:<name>` | `.claude/skills/<name>/SKILL.md` (repo) → else `~/.claude/skills/<name>/SKILL.md` |
| `file:<path>` | repo-relative markdown file |
| `learn` | derive from codebase exemplars → `learned_<slot>.md` (see Learn mode) |

## Resolution algorithm

```
1. repo .claude/standards.json exists ──────────────► read it, READ each resolved module, done
2. else ~/.claude/standards.json exists ────────────► present proposed slot mapping (gated)
                                                      on y: COPY to repo .claude/standards.json
3. else DISCOVER: scan repo + user skills dirs for
   frontmatter `metadata.standards-slot` ───────────► propose found modules per slot (gated);
                                                      interview per unmatched slot (Question/Why)
4. any slot mapped to `learn` or still unresolved ──► Learn mode (below)
5. write/refresh the repo manifest ─────────────────► subsequent runs hit step 1
```

Step 2/3 gates use the standard `Confirm: y/comment` sigil and the ≤120-line cap.

## Learn mode

For each learning slot:

1. **Pick exemplars** — the manifest `exemplars` list; else ask the user for 1-3 known-good directories; else select 2-3 central, recently-touched services.
2. **Derive conventions** — read the exemplars and extract the slot's conventions (for `styling`: naming, call style, typing; for `architecture`: layout, DI, boundaries; for `types`: suffixes in actual use; for `testing`: naming, fixtures, assertion style). Report what was *observed*, never what is assumed.
3. **Write** `docs/schematics/_standards/learned_<slot>.md`, structured like the corresponding module (headers + rules + one worked example from the repo itself).
4. **Gate it** — present a summary (≤120 lines), `Confirm: y/comment`. On y, point the manifest at it: `"<slot>": "file:docs/schematics/_standards/learned_<slot>.md"`.

## Binding consumption rules

- ENTERING any phase = having READ, in the current session, every resolved module that phase consumes (table above).
- QUOTE the rule **and its source module** when applying it: `python-standards: "NEVER default parameters"`.
- The project's CLAUDE.md (root + nested) is ALWAYS read in addition, and overrides modules on conflict.
- **Legacy fallback** — no manifest anywhere and the user declines Phase 0: the project CLAUDE.md (root + nested) + `~/.claude/CLAUDE.md` are the standards, as before.
