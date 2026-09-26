# Milestones — Phase 7 first-class, CLI-enforced

Plan for the `feat/milestones` feature: a named checkpoint over a set of task groups. Auto
mode drains the board up to the milestone, stops, and hands the user a report plus everything
needing an answer. Nothing past the boundary starts until they sign off. Optional — absent a
`## Milestones` table nothing changes.

All `file:line` citations are against the tree as of this plan (`scripts/schematic` 2,825 lines).

---

## 1. Data shapes

### 1.1 `tasks.md` — the `## Milestones` table (membership is content, not state)

Placement: immediately after the `## Task graph` section (after the critical-path fenced
block) and before `## Detailed Task Blocks`. Rationale: it is part of the map the user holds,
and the existing `## Task graph` / `## Detailed Task Blocks` H2s already prove a `##` heading
with no ` | ` is invisible to `TASK_HEADER_RE` (`scripts/schematic:115`), so the section
cannot collide with the task parser.

```markdown
## Milestones

| Milestone | Title | Scope | Proves |
|---|---|---|---|
| M1 | Resolver reachable | a, b | A YouTube caption-miss returns provider text through the real client. |
| M2 | Recovery wired and persisted | c, d | An ingestion run stores a recovered transcript with its source. |
| M3 | Composition and live probe | e, f | Every root builds; the paid probe returns text from a known-miss reel. |
```

- `Milestone` — `M<n>`, sequential from `M1`, no gaps. Row order IS milestone order.
- `Scope` — comma-separated **group letters** (`a`) and/or **explicit tags** (`c.1`). An
  explicit tag beats a group letter when both could claim it (lets one task be pulled forward
  without splitting a group).
- `Proves` — one sentence: what shipping this milestone demonstrates.

Source-of-truth split mirrors tasks exactly: `tasks.md` holds membership, the state file holds
gate state. Same division as `Status:` in `tasks.md` vs `state["tasks"][tag]["status"]`.

### 1.2 `.schematic-state.json` — `milestones`

```json
"milestones": {
  "decision": "yes",
  "decided_at": "2026-09-26T10:00:00+00:00",
  "proposed_at": "2026-09-26T10:04:00+00:00",
  "locked_at": "2026-09-26T10:06:00+00:00",
  "signed_off": { "M1": "2026-09-27T18:20:00+00:00" },
  "reported": { "M1": "2026-09-27T18:11:00+00:00" },
  "announced": { "M1": "2026-09-27T18:11:02+00:00" },
  "suite": { "M1": "155 passed, 0 failed in 4.42s" },
  "amendments": [
    { "at": "2026-09-28T09:00:00+00:00", "delta": "moved d.4 from M2 to M3", "reason": "d.4 needs e.1's root" }
  ]
}
```

`"milestones": null` = no decision recorded = every milestone mechanism off (M.6).
`load_state` (`scripts/schematic:169`) gains `loaded_state.setdefault("milestones", None)` and
the no-file default dict gains `"milestones": None` — same legacy-migration pattern the `run`
and `sweeps` keys already use (lines 172-176, covered by
`test_load_migrates_legacy_state_with_run_and_sweeps_keys`, `test_schematic.py:219`).

One extra key on an existing record: each sweep record in `state["sweeps"]` gains
`"milestone": "<id>" | null`, stamped at sweep time in `_review_sweep`
(`scripts/schematic:1975-2003`). This is the only mechanical way to say "the group standards
sweep is clean **for its groups**" — `phase_8_implementation_loop.md:279-286` establishes that
the CLI cannot map a group to file paths, so the sweep is scoped by *when it ran*, and the open
milestone at that moment is exactly the set of groups draining.

### 1.3 New module-level shapes (`scripts/schematic`, beside `parse_tasks`)

```python
MILESTONES_HEADING = "## Milestones"
MILESTONE_ID_RE = re.compile(r"^M\d+$")
MILESTONE_ROW_RE = re.compile(r"^\|\s*(M\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$")
MILESTONE_SCOPE_GROUP_RE = re.compile(r"^[a-z]$")
MILESTONE_SCOPE_TAG_RE = re.compile(r"^[a-z]\.\d+$")
MILESTONE_DECISION_YES = "yes"
MILESTONE_DECISION_NO = "no"
VALID_MILESTONE_DECISIONS = {MILESTONE_DECISION_YES, MILESTONE_DECISION_NO}
MILESTONE_REPORT_HEADING_PREFIX = "## Milestone "
DASHBOARD_LOG_FILENAME = ".milestone-dashboard.log"
OVERVIEW_URL_LOG_PREFIX = "Schematic overview: "

@dataclass(frozen=True)
class Milestone:
    id: str
    title: str
    scope: tuple[str, ...]
    proves: str
```

`FeatureStrip` (`scripts/schematic:508`) is the precedent for a frozen dataclass produced by a
markdown parser.

---

## 2. CLI surface — `schematic milestone …`

Wired in `_build_parser` (`scripts/schematic:2621`) between the `task` and `review` groups, and
into `dispatch` (`:2801`) as `"milestone": cmd_milestone`. `cmd_milestone` dispatches a
handler dict exactly like `cmd_task` (`:1320`) and `cmd_review` (`:1857`).

```
schematic milestone decide   yes|no        --schematic NAME
schematic milestone propose                --schematic NAME
schematic milestone lock                   --schematic NAME
schematic milestone status                 --schematic NAME
schematic milestone sign-off <id>          --schematic NAME
schematic milestone report   <id>          --schematic NAME [--suite "<last lines>"]
schematic milestone amend                  --schematic NAME --reason WHY
                                           ( --move TAGS --to ID | --add ID --title T --scope S --proves P )
```

### argparse shape

```python
p_milestone = sub.add_parser("milestone", help="Multi-stage delivery gate (Phase 7 decision, Phase 8 boundary)")
milestone_sub = p_milestone.add_subparsers(dest="milestone_command", required=True)

p_mdecide = milestone_sub.add_parser("decide", help="Record the Phase-7 answer: split this task set into milestones?")
p_mdecide.add_argument("answer", choices=sorted(VALID_MILESTONE_DECISIONS))
p_mdecide.add_argument("--schematic", required=True, metavar="NAME")

p_mpropose = milestone_sub.add_parser("propose", help="Validate the ## Milestones table and echo the resolved membership for the gate")
p_mpropose.add_argument("--schematic", required=True, metavar="NAME")

p_mlock = milestone_sub.add_parser("lock", help="Lock the proposed milestones on the user's y")
p_mlock.add_argument("--schematic", required=True, metavar="NAME")

p_mstatus = milestone_sub.add_parser("status", help="Per-milestone task counts, gate state, and the open milestone")
p_mstatus.add_argument("--schematic", required=True, metavar="NAME")

p_msignoff = milestone_sub.add_parser("sign-off", help="Sign off a drained milestone (opens the next one)")
p_msignoff.add_argument("id", metavar="MILESTONE", help="Milestone id (e.g. M1)")
p_msignoff.add_argument("--schematic", required=True, metavar="NAME")

p_mreport = milestone_sub.add_parser("report", help="Write the milestone section of implementation_report.md and print it")
p_mreport.add_argument("id", metavar="MILESTONE", help="Milestone id (e.g. M1)")
p_mreport.add_argument("--schematic", required=True, metavar="NAME")
p_mreport.add_argument("--suite", metavar="LAST_LINES", help="The test suite's last line(s) as run for this milestone")

p_mamend = milestone_sub.add_parser("amend", help="Post-lock re-scope: move tasks between milestones, or add one")
p_mamend.add_argument("--schematic", required=True, metavar="NAME")
p_mamend.add_argument("--reason", required=True, metavar="WHY", help="Why the scope changed")
p_mamend.add_argument("--move", metavar="TAGS", help="Comma-separated task tags to move")
p_mamend.add_argument("--to", metavar="MILESTONE", help="Destination milestone id for --move")
p_mamend.add_argument("--add", metavar="MILESTONE", help="New milestone id to append")
p_mamend.add_argument("--title", metavar="TITLE", help="Title for --add")
p_mamend.add_argument("--scope", metavar="SCOPE", help="Comma-separated groups/tags for --add")
p_mamend.add_argument("--proves", metavar="TEXT", help="What --add proves")
```

`--move`/`--add` are validated in the handler (`_exit_error` on neither, both, or an incomplete
set) rather than via `add_mutually_exclusive_group`, matching how `_review_start` validates
`--auto` needing `--goal` (`scripts/schematic:1875`). No mutually-exclusive group appears
anywhere in the current parser.

### Refusal conditions (every one exits 1 via `_exit_error`, `scripts/schematic:596`)

| Command | Refuses when |
|---|---|
| `decide` | the milestones are already locked (`locked_at` set) — post-lock re-scope is `amend`. An unknown answer is refused by argparse `choices` (exit 2). |
| `propose` | no decision recorded; decision is `no`; no `## Milestones` table in `tasks.md`; ids not sequential from `M1`; a scope token is neither a group letter nor a task tag; a task belongs to no milestone; a task belongs to two; a task's `Blocked by:` names a task in a LATER milestone. |
| `lock` | decision is not `yes`; `propose`'s validation does not pass (re-run in full — lock never trusts a stale `proposed_at`); already locked. |
| `status` | never refuses. Prints `no milestones declared` when `milestones` is `null` or the decision is `no`. |
| `sign-off` | no locked milestones; unknown id (prints the known ids); already signed off; an EARLIER milestone is unsigned; any task of the milestone is not `complete`; any task is `pendingInput`; any task lacks a `clean` per-task review verdict (M.9); the run is `auto` and no sweep stamped with this milestone is `pristine` (M.9). |
| `report` | no locked milestones; unknown id. (Does NOT require the milestone to be drained — a mid-milestone report is a legitimate read.) |
| `amend` | the milestones are not locked; neither `--move` nor `--add` given; both given; `--move` without `--to` (or vice versa); `--add` without all of `--title`/`--scope`/`--proves`; a moved tag is not a task; `--to`/`--add` id is not `M<n>`; the resulting membership would leave a task in no milestone or in two; the destination milestone is already signed off; `--add`'s id already exists. |

### Print shapes

Every handler ends with the next command, as every existing handler does (`_phase_audit:1225`,
`_task_complete:1648`, `_review_start:1892`). `decide yes` → `next: write the ## Milestones
table, then schematic milestone propose …`; `decide no` → `delivering as one stage — next:
schematic phase complete 7 …`; `propose` → the resolved membership table + `on the user's y:
schematic milestone lock …`; `lock` → `next: schematic phase complete 7 …`.

---

## 3. Where each AC lands

| AC | File · function | New or existing |
|---|---|---|
| **M.0** decision recorded, `phase complete 7` refuses | `scripts/schematic` · `cmd_milestone`, `_milestone_decide` | new (new `# ── milestone commands ──` section after the task commands, before the Q&A relay at `:1730`) |
| | `scripts/schematic:1244` · `_phase_complete` | existing — a new check after the sign-off check (`:1261-1270`) and before the artifact checks (`:1272`), guarded `if args.num == PLANNING_FINAL_PHASE` (`:73`). Honours `--override` + `record_override` exactly like its siblings. |
| **M.1** proposal + lock + validate rules | `scripts/schematic` · `parse_milestones`, `_tag_to_milestone_id`, `_milestone_propose`, `_milestone_lock` | new (`parse_milestones` beside `parse_tasks`, `:454`, under the `# ── markdown parsers ──` banner) |
| | `scripts/schematic:945` · `_validate_schematic` | existing — one added `findings.extend(_milestone_findings(...))`; the rules live in a new `_milestone_findings(schematic_dir, tasks)` helper beside `_open_input_findings` (`:924`), so `_validate_schematic` does not grow. |
| **M.2** hard stop at the boundary | `scripts/schematic:1651` · `_task_next` | existing — a milestone filter in the pending scan, then boundary detection when nothing is servable. Helpers `_open_milestone(state, milestones)` and `_milestone_of_task(tag, tag_to_milestone_id)` keep `_task_next` inside the method ceiling. |
| | `scripts/schematic` · `_milestone_signoff` | new |
| **M.3** milestone report | `scripts/schematic` · `_milestone_report`, `_render_milestone_report`, `_write_report_section` | new |
| | `scripts/schematic:454` · `parse_tasks` | existing — parse the `Divergence:` line `schematic-task-done` already writes (`scripts/schematic-task-done:126-133`) into `task["divergence"]` (default `None`). Fourth parsed key; `phase_7_tasks.md:79` ("these three bare keys") is updated with it. |
| | `scripts/schematic:1714` · `_print_decision_ledger` | existing — the per-tag collection is extracted to `_tag_to_decisions(state, tags)` so both the ledger printer and the report use one source. |
| | `scripts/schematic:1747` · `_pending_questions` | existing — the returned dict gains `"tag": question.get("tag", "")`; `_file_task_question` already writes `tag` (`:1343`). Lets the report filter open questions to the milestone's tasks. |
| **M.4** dashboard Reports area | `scripts/overview.py:190` · `_build_manifest` | existing — `implementation_report.md` added to the `files` scan list. That is the only server change; the tab reads `/api/state` (`:87`) and `/api/file` (`:65`), both already open. |
| | `reference/overview_ui/overview.html` · new `showReports()`, `parseMilestonesFromMarkdown()`, nav entry in `buildSidebar` (`:261`), routes in `navigate` (`:416`) + `restoreFromHash` (`:249`) for `#reports` and `#milestone:<id>` | new functions in the existing file; the Q&A bubble is mounted the way `openTaskModal` (`:752`) mounts it. |
| **M.5** kanban carries the milestone | `reference/overview_ui/overview.html:696` · `parseTasksFromMarkdown` (+ `milestone` per task), `:729` `renderKanbanCard` (tag chip), `:647` `showKanban` (group-by-milestone toggle → one board per milestone, reusing `.kanban-board`, CSS `:106`) | existing |
| **M.6** optional + backward compatible | every read guarded on `state["milestones"]` being non-`null` with a `yes` decision AND a non-empty table; `parse_milestones` returns `[]` for a bundle with no section | — |
| **M.7** docs + tests | §6, §7 below | — |
| **M.8** amend | `scripts/schematic` · `_milestone_amend`, `_rewrite_milestone_table(tasks_md, milestones)` | new |
| **M.9** review layers at the boundary | `_milestone_signoff` refusals (above) + the doc split in `phase_8_implementation_loop.md` | — |
| **M.10** auto-open on a hit | `scripts/schematic` · `_launch_milestone_dashboard(schematic_dir, milestone_id)`; `_await_editor_url` (`:2539`) and `_editor_url_in_log` (`:2560`) gain a `url_prefix` parameter (one existing call site updated, `:2532`) | new + existing |
| | `scripts/overview.py:285` · `launch_overview(schematic_dir, fragment)`; `scripts/schematic:2354` · `cmd_overview` passes `args.fragment`; `_build_parser` adds `--fragment` to `overview` | existing |

### 3.1 The boundary mechanism (M.2 · M.3 · M.10 in one place)

`schematic-task-done` — the driver loop's completion step
(`phase_8_implementation_loop.md:248`) — writes `tasks.md` and never touches
`.schematic-state.json` (`scripts/schematic-task-done:151-172`; it only *reads* state, `:136`).
So "when the last task of a milestone completes" cannot hook `task complete`: half the
completions do not go through it. The hook is `_task_next`, which the driver loop calls every
iteration and which M.2 already makes the loop's exit point:

```
_task_next(name, peek)
  milestones = parse_milestones(tasks.md)           # [] → today's behaviour verbatim (M.6)
  open_milestone = first milestone with no signed_off entry
  scan pending tasks:
      skip a task whose milestone != open_milestone   # M.2 — also under --peek
      first unblocked one wins → claim + print (unchanged)
  nothing servable in ANY bundle:
      for the first bundle whose open milestone is fully complete:   # deterministic: sorted dir order
          write/refresh its report section          # M.3
          print the report in full                  # the terminal has it regardless of the browser
          launch the dashboard on #milestone:<id>   # M.10
          print: schematic milestone sign-off <id> --schematic <name>
      else: "no pending unblocked tasks found" (unchanged) + the open milestone's held tasks
```

Multi-bundle rule: a servable task **anywhere** beats a boundary report. `_task_next` iterates
`_resolve_single_or_all` (`:601`, `:1654`) and today `return`s from inside that loop — the
milestone filter must `continue` to the next bundle, not return, or a gated bundle would hide
every other bundle's work.

Dashboard launch, fail-closed: the report is written and printed BEFORE the launch, then
`_launch_milestone_dashboard` spawns the CLI's own `overview` subcommand detached and waits for
its URL line, reusing the roster launcher's idiom verbatim (`_launch_roster_editor:2514`,
`_await_editor_url:2539`, `start_new_session=True`, `EDITOR_LAUNCH_TIMEOUT_SECONDS:101`):

```python
subprocess.Popen(
    ["python3", str(Path(__file__).resolve()), "overview", schematic_dir.name, "--fragment", f"milestone:{milestone_id}"],
    stdout=(schematic_dir / DASHBOARD_LOG_FILENAME).open("w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
```

A launch that never reports a URL exits via `_exit_error` — the same fail-closed posture the
roster gate takes ("nothing presented"), and nothing is lost because the report is already on
disk and on screen. `launch_overview` blocks on `serve_forever` (`overview.py:346`), which is
why this must be a detached child and never an in-process call.

Idempotency: the boundary fires once per milestone — `state["milestones"]["announced"][id]`
guards the announcement + launch; `state["milestones"]["reported"][id]` is only the write receipt,
so an explicit mid-stage `milestone report` never disarms the boundary. An amendment that changes a
milestone's membership clears its `announced` entry, so a re-drained milestone is reported and
presented again. `schematic milestone report <id>` always rewrites (it is the explicit re-read
path) and never launches a browser.

### 3.2 Report section shape (M.3)

Written into `implementation_report.md` at the bundle root (already a Phase-8 artifact check,
`scripts/schematic:82`, and already lint-scanned, `:123`). Section replaced in place when its
heading exists, appended otherwise — so re-running never duplicates and never clobbers the
final report's own body.

```markdown
## Milestone M1 — Resolver reachable

Proves: A YouTube caption-miss returns provider text through the real client.
Scope: groups a, b — 9 tasks.

### Tasks
| Tag | Action | Target | Divergence |
|---|---|---|---|
| a.1 | Modify | src/shared/clients/reels/models.py | — |
| b.2 | Create | GroqTranscriptionClient | patched-in-component-file |

### Autonomous decisions
- a.2: named the routing table PLATFORM_TO_PROVIDER — the card left it unnamed (naming)

### Review verdicts
- a.1: clean — no findings
- b.2: clean — two naming findings fixed

### Standards sweep
sweep 3: PRISTINE ✓ (4 batches)

### Test suite
155 passed, 0 failed in 4.42s

### Open questions
- tasks#2 (b.3): which timeout does the signed-MP4 fetch inherit?
```

Empty subsections render `— none` rather than being omitted, so the reader can tell "nothing
to report" from "not recorded". `### Test suite` renders `not recorded` when no `--suite` text
has been given for this milestone (see GATE 1).

---

## 4. Dashboard changes

**Reports tab (M.4).** New sidebar nav group `Reports`, shown only when the manifest reports
`implementation_report.md` or the `## Milestones` table is non-empty. `showReports()` renders:

- one entry per milestone — id, title, proves, gate state (`open` / `drained, awaiting sign-off`
  / `signed off <date>`), and the milestone's report section body rendered through
  `marked` + `DOMPurify` (the `showFile` path, `:482`), read by splitting
  `implementation_report.md` on `MILESTONE_REPORT_HEADING_PREFIX`;
- one entry for the final report — everything in `implementation_report.md` outside a milestone
  section;
- a status header: phase (from `/api/state` `phases`, same arithmetic as `_print_status:818-822`),
  gate state, and the current milestone.

The existing `QABubble` is mounted inline in each entry exactly as `openTaskModal` mounts it
(`:789-822`), so Q&A works there with no new relay plumbing.

**Kanban (M.5).** `parseTasksFromMarkdown` gains a `milestone` field, resolved client-side from
the `## Milestones` table by the same group-letter/explicit-tag rule as the CLI.
`renderKanbanCard` renders the id as a chip next to the tag. `showKanban` gains a
`Group by milestone` toggle that renders one `.kanban-board` per milestone under an id + title
header instead of a single board.

**Deep link (M.10).** `#milestone:<id>` in `restoreFromHash` (`:249`) opens the Reports tab
scrolled to that milestone; `#reports` opens the tab. `launch_overview` gains a `fragment`
parameter appended to the URL it opens, passed `""` by a bare `schematic overview`.

---

## 5. Constraints honoured / where repo idiom wins

- **No parallel task model.** Membership is four columns in `tasks.md`; gate state is one key in
  `.schematic-state.json`; the only new parsed task key is `Divergence:`, which
  `schematic-task-done` already writes today.
- **`~/.claude/skills/python-standards` "General" + "Naming":** full typing, no `Any`, no
  default parameters (including the new `url_prefix` and `fragment` parameters — every call
  site passes them), dicts named `key_to_value` (`tag_to_milestone_id`, `id_to_milestone`,
  `tag_to_decisions`), results named as state (`open_milestone`, `signed_off_ids`), no magic
  literals (every regex, heading and log name is a module constant), one-line docstrings on the
  new helpers.
- **Repo idiom wins over the trengine service tree, explicitly:** this is a single-file stdlib
  CLI, so (a) handlers stay module-level `_verb_noun(args)` functions dispatched from a dict —
  no service classes, no DI; (b) `dict[str, Any]` (`TaskRecord`, `:21`) stays the task/state
  currency rather than dataclasses, because `load_state`/`save_state` round-trip raw JSON;
  (c) refusals are `_exit_error(...)` + `sys.exit(1)`, not typed exceptions;
  (d) `_validate_schematic` already exceeds the 35-line method ceiling, so the new rules go in a
  helper instead of growing it.
- **No new try/except.** Every new path reads state the existing loaders already normalise;
  malformed input is refused with `_exit_error`, not guarded.
- **Tests:** repo idiom wins over `writing-tests` §2/§7 where they collide — `unittest.TestCase`
  classes with `self.assertEqual`, `TemporaryDirectory`, the existing `_make_schematic_dir` /
  `_make_args` / `_with_resolved_dir` / `_captured_stdout` helpers (`test_schematic.py:124-178`),
  and `_make_*` factory names (writing-tests mandates `_gen_*`; every one of the 155 existing
  tests uses `_make_*`, and mixing conventions in one file is worse than either). What carries
  over from `writing-tests`: the test-case list first (§0, this document), exact assertions on
  whole objects (§8), one scenario per name with its qualifying condition (§7), and `# Given` /
  `# When` / `# Then` blocks where the existing file already uses them.

---

## 6. Docs edits (M.7)

| File | Edit |
|---|---|
| `README.md` | "The kit" / pipeline prose: one line that Phase 7 can split delivery into milestones and Phase 8 stops at each. CLI block (`:122-136`): add `schematic milestone decide\|propose\|lock\|status\|sign-off\|report\|amend`. Enforcement-gates table (`:110-121`): three rows — `phase complete 7` milestone decision, `task next` milestone boundary, `milestone sign-off` review + sweep requirement. |
| `SKILL.md` | Caution-block command groups (`:19-25`): add the `milestone` line. "Schematic File Structure → `tasks.md`" (`:537-555`): add the `## Milestones` table with the scope rule. Write-routing table (`:131`): Phase 7 also writes the Milestones table. Change Propagation Guide (`:563-593`): a "Milestone scope changed" row → `tasks.md` (table) + `schematic milestone amend`. |
| `phase_7_tasks.md` | CLI gate commands blockquote (`:3-8`): the milestone commands. A new binding step after the graph gate (`:51`): the exact question — *"Split this task set into a multi-stage delivery using milestones?"* — recorded with `schematic milestone decide yes\|no`, the `no` path, the M.1 proposal shape (table columns + the `y` → `lock`), and the rule that `schematic phase complete 7` refuses without a recorded decision. |
| `phase_8_implementation_loop.md` | Driver loop (`:239-249`): the loop exits at a milestone boundary by construction. New `### Milestone boundary` subsection under Auto mode: the report, the sign-off command, and the review-layer split. Four-review-layers table (`:261-266`): layers #1 + #2 are boundary requirements per milestone; #3 (consistency) and #4 (entry-point tracing) stay at feature end — and say why (duplication and cross-path correctness are whole-feature properties a partial diff cannot see). |

---

## 7. Test-case list (`scripts/test_schematic.py`)

80 cases. Tier 1 = AC tests; Tier 2 = branch tests. New classes are appended in the file's
existing order convention (one class per command area, fixtures at the top of the class).

Two shared fixtures are added beside `_make_schematic_dir` (`:124`):
`_MILESTONES_MD` (a three-milestone table over the existing `_TASKS_MD` groups a/b) and
`_make_milestoned_schematic_dir(tmp)` (bundle + table + a recorded `yes` decision).

### Tier 1 — AC tests

**`TestParseMilestones`** (M.1 parser)
1. `test_parses_every_row_of_the_milestones_table` — three-row table → three `Milestone` records equal to the expected objects.
2. `test_parses_group_letters_and_explicit_tags_in_one_scope` — `a, c.1` → `("a", "c.1")`.
3. `test_returns_empty_list_when_no_milestones_section` — `tasks.md` without the heading → `[]`.
4. `test_returns_empty_list_when_file_missing` — absent `tasks.md` → `[]`.

**`TestMilestoneMembership`** (M.1 resolution)
5. `test_maps_every_task_to_its_milestone_by_group_letter` — scopes `a` / `b` → exact `tag_to_milestone_id` dict.
6. `test_explicit_tag_scope_wins_over_group_scope` — M1 `a`, M2 `a.2` → `a.1→M1`, `a.2→M2`.

**`TestMilestoneDecideGate`** (M.0)
7. `test_phase_7_complete_fails_without_a_milestone_decision` — audit + sign-off present, no decision → `SystemExit`, phase 7 unlocked.
8. `test_phase_7_complete_locks_after_deciding_no` — decision `no` → phase 7 locked.
9. `test_phase_7_complete_locks_after_deciding_yes_and_locking_the_milestones` — decision `yes` + `locked_at` → locked.
10. `test_phase_7_complete_fails_when_yes_was_decided_but_the_milestones_are_unlocked` — `yes`, no lock → `SystemExit`.
11. `test_phase_7_complete_locks_with_override_despite_a_missing_decision` — `--override` → locked + one override recorded.
12. `test_phase_6_complete_does_not_require_a_milestone_decision` — phase 6 audit + sign-off → locked.
13. `test_decide_records_the_answer_and_its_timestamp` — `decide yes` → `decision == "yes"`, `decided_at` present.
14. `test_decide_refuses_after_the_milestones_are_locked` — `locked_at` set → `SystemExit`, decision unchanged.

**`TestMilestonePropose`** (M.1)
15. `test_propose_echoes_the_resolved_membership_for_every_milestone` — stdout names each id with its tags.
16. `test_propose_refuses_when_the_decision_is_no` → `SystemExit`.
17. `test_propose_refuses_when_no_decision_is_recorded` → `SystemExit`.
18. `test_propose_refuses_when_the_table_is_missing` — decision `yes`, no section → `SystemExit`.
19. `test_propose_refuses_a_task_in_no_milestone` — uncovered tag → `SystemExit` naming it.
20. `test_propose_refuses_a_task_in_two_milestones` — overlapping scopes → `SystemExit` naming it.
21. `test_propose_refuses_a_dependency_on_a_later_milestone` — M1 task blocked by an M2 task → `SystemExit`.
22. `test_propose_accepts_a_dependency_on_an_earlier_milestone` — M2 task blocked by an M1 task → clean.
23. `test_propose_refuses_non_sequential_milestone_ids` — `M1`, `M3` → `SystemExit`.

**`TestMilestoneLock`** (M.1)
24. `test_lock_records_the_lock_timestamp` — `locked_at` present.
25. `test_lock_refuses_before_a_yes_decision` → `SystemExit`, `locked_at` absent.
26. `test_lock_refuses_when_membership_is_incomplete` — uncovered tag → `SystemExit`, `locked_at` absent.
27. `test_lock_refuses_when_already_locked` → `SystemExit` pointing at `amend`.

**`TestMilestoneBoundary`** (M.2 · M.3 · M.10, `_launch_milestone_dashboard` patched)
28. `test_task_next_claims_a_task_from_the_open_milestone` — first unblocked M1 task claimed.
29. `test_task_next_serves_nothing_from_a_later_milestone_until_sign_off` — M1 complete, M2 pending → no claim, M2 task still `pending`.
30. `test_task_next_serves_the_next_milestones_task_after_sign_off` — M1 signed off → M2 task claimed.
31. `test_task_next_at_the_boundary_writes_the_report_and_opens_the_dashboard` — `implementation_report.md` gains the section; the launcher is called with the milestone id.
32. `test_task_next_at_the_boundary_prints_the_sign_off_command` — stdout carries `milestone sign-off M1`.
33. `test_task_next_ignores_milestones_when_none_are_declared` — no table → today's behaviour, launcher never called.
34. `test_task_next_peek_does_not_look_past_the_boundary` — `--peek` → no M2 task printed, no status change.
35. `test_task_next_does_not_fire_the_boundary_twice_for_one_milestone` — second call → launcher called once, one report section.
36. `test_task_next_serves_a_second_bundles_task_before_a_gated_bundles_boundary` — all-bundles scan: a servable task beats a boundary report.

**`TestMilestoneSignOff`** (M.2 · M.9)
37. `test_sign_off_records_the_milestone_when_every_gate_is_clean` — `signed_off["M1"]` present.
38. `test_sign_off_refuses_while_a_task_is_incomplete` → `SystemExit`.
39. `test_sign_off_refuses_while_a_task_is_pending_input` → `SystemExit`.
40. `test_sign_off_refuses_when_a_task_has_no_clean_review_verdict` → `SystemExit` naming the tag.
41. `test_sign_off_refuses_in_auto_mode_when_no_sweep_for_the_milestone_is_pristine` → `SystemExit`.
42. `test_sign_off_succeeds_in_auto_mode_when_the_milestones_sweep_is_pristine` → recorded.
43. `test_sign_off_does_not_require_a_sweep_in_manual_mode` → recorded (GATE 2).
44. `test_sign_off_refuses_when_an_earlier_milestone_is_unsigned` → `SystemExit`.
45. `test_sign_off_refuses_an_unknown_milestone_id` → `SystemExit` listing the known ids.
46. `test_sign_off_refuses_when_already_signed_off` → `SystemExit`.

**`TestMilestoneReport`** (M.3)
47. `test_report_writes_a_section_naming_every_task_of_the_milestone` — tags, actions, targets present; another milestone's tags absent.
48. `test_report_carries_each_tasks_divergence_flag` — a `Divergence: bridged-not-patched` task renders its flag.
49. `test_report_lists_the_autonomous_decisions_of_the_milestones_tasks_only`.
50. `test_report_lists_each_tasks_review_verdict_and_summary`.
51. `test_report_records_the_sweep_result_for_the_milestone` — the milestone-stamped sweep's PRISTINE state.
52. `test_report_lists_the_open_questions_of_the_milestones_tasks`.
53. `test_report_records_the_suite_last_lines_passed_on_the_command` (GATE 1).
54. `test_report_replaces_its_own_section_on_a_second_run` — one heading occurrence, new body.
55. `test_report_preserves_the_rest_of_the_implementation_report` — pre-existing prose intact.
56. `test_report_creates_the_implementation_report_when_absent`.
57. `test_report_refuses_an_unknown_milestone_id` → `SystemExit`.
58. `test_report_does_not_launch_the_dashboard` — patched launcher never called.

**`TestMilestoneAmend`** (M.8)
59. `test_amend_moves_a_tag_to_another_milestone_in_tasks_md` — the table's scope cells are rewritten; membership resolves to the new owner.
60. `test_amend_expands_a_group_scope_into_its_remaining_tags_when_a_tag_leaves` — M1 scope `a` minus `a.2` → `a.1, a.3`.
61. `test_amend_adds_a_new_milestone_row_at_the_end_of_the_table`.
62. `test_amend_records_the_delta_and_reason_in_state` — one `amendments` entry with `at`/`delta`/`reason`.
63. `test_amend_refuses_before_the_milestones_are_locked` → `SystemExit`.
64. `test_amend_refuses_a_move_that_leaves_a_task_in_no_milestone` → `SystemExit`, `tasks.md` unchanged.
65. `test_amend_refuses_a_move_into_a_signed_off_milestone` → `SystemExit`.
66. `test_amend_refuses_without_either_a_move_or_an_add` → `SystemExit`.
67. `test_amend_refuses_an_add_missing_its_title_scope_or_proves` → `SystemExit`.

**`TestMilestoneValidate`** (M.1 validate rules · M.6)
68. `test_validate_flags_a_task_in_no_milestone`.
69. `test_validate_flags_a_task_in_two_milestones`.
70. `test_validate_flags_a_dependency_on_a_later_milestone`.
71. `test_validate_flags_a_scope_token_that_is_neither_a_group_nor_a_tag`.
72. `test_validate_flags_a_scope_group_matching_no_task`.
73. `test_validate_is_clean_when_no_milestones_are_declared`.

**`TestMilestoneStatus`**
74. `test_status_prints_each_milestone_with_its_task_counts_and_gate_state`.
75. `test_status_names_the_open_milestone`.
76. `test_status_reports_no_milestones_when_none_are_declared`.

### Tier 2 — branch tests

77. `TestStateIO::test_load_migrates_legacy_state_without_a_milestones_key` — a pre-feature state file loads with `milestones` `None`.
78. `TestReviewSweep::test_sweep_stamps_the_open_milestone_on_the_sweep_record` — sweep record `milestone == "M1"`.
79. `TestReviewSweep::test_sweep_stamps_no_milestone_when_none_are_declared` — sweep record `milestone` is `None`.
80. `TestParseMilestones::test_parses_a_row_whose_cells_carry_extra_whitespace` — padded cells → trimmed fields.

Two further branch cases fall out of argparse `choices` and need no test of their own
(`decide bogus` → exit 2), consistent with the existing suite, which never tests argparse
validation directly.

---

## 8. ASSUMES (each confirmed against the tree)

| # | Assumption | Status |
|---|---|---|
| A1 | A `##` heading with no ` \| ` is invisible to the task parser, so `## Milestones` cannot become a phantom task. | **Confirmed** — `TASK_HEADER_RE` requires two ` \| ` separators (`scripts/schematic:115`); the live bundle's `## Task graph` and `## Detailed Task Blocks` headings already prove it (`docs/schematics/reel_transcription/tasks.md:5,61`). |
| A2 | `load_state` normalises missing keys on read, so a new key needs no migration script. | **Confirmed** — `setdefault` for `run` and `sweeps` (`scripts/schematic:174-176`), with a legacy test at `test_schematic.py:219`. |
| A3 | `schematic-task-done` does not update `.schematic-state.json`, so task completion cannot be hooked there. | **Confirmed** — it reads state only (`scripts/schematic-task-done:136-148`) and writes `tasks.md` (`:172`). |
| A4 | The CLI does not currently write `implementation_report.md`; the agent does. | **Confirmed** — the only references are the Phase-8 artifact existence check (`scripts/schematic:82`), the ratification lint list (`:123`), and print-only guidance (`:1724`). M.3 makes the CLI a writer of that file for the first time; hence the replace-in-place rule. |
| A5 | Nothing in the CLI or state records test-suite output today. | **Confirmed** — no `suite` key anywhere in `scripts/schematic`; the only mentions of "suite" are prose in `phase_8_implementation_loop.md:93,243,343`. → GATE 1. |
| A6 | Sweeps are structurally auto-mode-only. | **Confirmed** — `_require_auto_run` (`scripts/schematic:1941`) exits unless `run.mode == auto`, and `_review_sweep` calls it first (`:1957`). → GATE 2. |
| A7 | The CLI cannot map a task group to file paths, so a sweep cannot be scoped to a group by argument. | **Confirmed** — stated as a design ruling in `phase_8_implementation_loop.md:282-286`. Hence the time-stamped `milestone` field on the sweep record. |
| A8 | `launch_overview` blocks forever, so the dashboard must be launched as a detached child. | **Confirmed** — `server.serve_forever()` (`scripts/overview.py:346`); the roster gate already spawns a blocking UI detached (`scripts/schematic:2524-2529`). |
| A9 | The dashboard can read milestone gate state and the report with no new endpoint. | **Confirmed** — `/api/state` serves the whole state file (`scripts/overview.py:87-94`) and `/api/file` serves any bundle-relative file (`:65-76`); only the manifest's `files` scan list needs `implementation_report.md` (`:190`). |
| A10 | The task Q&A relay records the asking task's tag, so the report can filter questions per milestone. | **Confirmed** — `_file_task_question` writes `"tag": tag` (`scripts/schematic:1343`); `_pending_questions` currently drops it (`:1767-1774`) and gains it back. |
| A11 | `phase complete` gates are overridable, so the M.0 refusal has a documented escape hatch and legacy bundles are never stuck. | **Confirmed** — every existing check honours `--override` + `record_override` (`:1250-1304`). A bundle whose phase 7 is already locked never re-runs the command (e.g. `reel_transcription`, phase 7 `locked`, `milestones` absent). |
| A12 | The suite runs green before the change, and `python3 -m pytest` is NOT the runnable command on this machine. | **Confirmed** — `python3 -m unittest discover -s scripts -p "test_schematic*.py"` → `Ran 155 tests … OK`; `python3 -m pytest` fails with `No module named pytest` (README `:211-215` names pytest; a standalone `/usr/local/bin/pytest` exists on a different interpreter). Not a plan item — flagged so T2 uses the runner that works. |

---

## 9. GATE questions

**GATE 1 — where do the report's "suite last-lines" come from?**
Why: M.3 lists "suite last-lines if recorded" in the report, but nothing in the CLI or state
records test-suite output today (A5), so the phrase has no referent and the section cannot be
built without new surface the ACs do not name.
Options: (a) `schematic milestone report <id> --suite "<last lines>"`, recorded in
`milestones.suite[<id>]` and rendered `not recorded` when absent — the shape this plan assumes;
(b) a separate `schematic milestone suite <id> "<text>"` recorder; (c) scrape `task note` text
behind a marker; (d) drop the line and let the agent paste suite output into the report by hand.
Implication: (a) adds one flag to a command that already exists and keeps the CLI the recorder
of record. (d) means the CLI-written section is not the whole record and an agent hand-edits a
CLI-owned section — the thing replace-in-place is designed to prevent.

**GATE 2 — does milestone sign-off require a PRISTINE sweep in manual mode?**
Why: M.9 makes "the group standards sweep recorded clean for its groups" a sign-off
requirement, but sweeps are structurally auto-mode-only (A6) — enforced literally, milestone
sign-off becomes impossible in manual mode, which M.6 says must keep working.
Options: (a) enforce the sweep condition only when `run.mode == auto`; in manual mode the
per-task clean verdicts are the standards layer that exists — the shape this plan assumes
(test 43); (b) enforce it always, which makes milestones an auto-mode-only feature; (c) lift
`_require_auto_run` off `review sweep` so manual runs can sweep too — a change to an existing
gate, outside this feature's scope.
Implication: (a) means a manual-mode milestone is gated by per-task reviews only, and the
sign-off print must say so explicitly rather than implying a sweep happened.

**GATE 3 — does `phase complete 8` require every milestone signed off?**
Why: the ACs gate `task next` on sign-off but say nothing about locking Phase 8 with an
unsigned milestone, and M.6 forbids changing existing behaviour for bundles without milestones.
Options: (a) no new check — Phase 8 locks on its existing artifact + sign-off gates, and an
unsigned milestone is visible in `milestone status` and the Reports tab (the shape this plan
assumes: no test, no code); (b) refuse `phase complete 8` while any milestone is unsigned.
Implication: (b) is a second enforcement point on the same fact and would need its own
`--override` path; (a) leaves "feature done with milestone 3 unsigned" reachable.

---

## 10. Out of scope (stated so it is not read as an omission)

- No change to `schematic-task-done` — it stays a `tasks.md` writer; the boundary is detected in
  `task next` (§3.1).
- No `--group` argument on `review sweep`; the sweep's milestone is stamped, never asked for (A7).
- No milestone concept in Phase 9 compression, `track`, or the audits.
- No re-ordering of milestones after lock; `amend` moves tasks and appends milestones only.
