#!/usr/bin/env python3

import argparse
import contextlib
import importlib.util
import io
import json
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import MagicMock, patch

# ── load CLI module (no .py extension) ────────────────────────────────────────

import importlib.machinery

_CLI_PATH = Path(__file__).parent / "schematic"
_loader = importlib.machinery.SourceFileLoader("schematic_cli", str(_CLI_PATH))
_spec = importlib.util.spec_from_loader("schematic_cli", _loader)
assert _spec is not None
_cli = importlib.util.module_from_spec(_spec)
_loader.exec_module(_cli)

# ── fixtures ───────────────────────────────────────────────────────────────────

_TASKS_MD = textwrap.dedent("""\
    # Tasks

    ## a.1 | Create | FoundationService
    Status: complete
    Component file: ./components/foundation_service.md

    ## b.1 | Create | ReelEnrichmentService.enrich_reels
    Status: pending
    Feature ACs: 1.A, 1.B
    Component file: ./components/reel_enrichment_service.md
    Blocked by: a.1 | Create | FoundationService

    ## b.2 | Create | AnotherService
    Status: pending
    Component file: ./components/another_service.md
    Blocked by: b.1 | Create | ReelEnrichmentService
""")

_OBJECTIVE_MD = textwrap.dedent("""\
    # Test Feature

    ## Context & Objective
    Context:
      - existing system
    Objective:
      - build enrichment

    ## Feature Change List + Feature ACs
    Part of change set: enrichment pipeline

    1. Enrich reels
       Class: ReelEnrichmentService
       Changes:
         1.A
           Title: Add enrichment
           What: enriches reels
           Why: needed

    ## Component Summary

    | # | Class | Type | Class AC | Necessitated by |
    |---|---|---|---|---|
    | 1.1 | FoundationService | Service | Provides foundation | 1.A |
    | 1.2 | ReelEnrichmentService | Service | Enriches reels | 1.A |

    ## Directory Structure
    src/
      services/
        enrichment/
          reel_enrichment_service.py (NEW)
""")

_VALID_SEQUENCE_MMD = textwrap.dedent("""\
    sequenceDiagram
    participant A
    participant B
    A->>B: request
    B-->>A: response
    loop retry
    A->>B: retry
    end
""")

_SEQUENCE_MISSING_DECL = textwrap.dedent("""\
    participant A
    A->>B: request
""")

_SEQUENCE_UNBALANCED_LOOP = textwrap.dedent("""\
    sequenceDiagram
    loop outer
    A->>B: first
    loop inner
    A->>B: nested
    end
""")

_SEQUENCE_BAD_NOTE = textwrap.dedent("""\
    sequenceDiagram
    participant A
    Note A: missing 'over'
""")

_VALID_FLOWCHART_MMD = textwrap.dedent("""\
    flowchart TD
    A --> B
    B --> C
""")

_INVALID_FLOWCHART_DECL = textwrap.dedent("""\
    graph
    A --> B
""")


def _make_schematic_dir(tmp: str, name: str = "test-feature") -> Path:
    schematic_dir = Path(tmp) / "docs" / "schematics" / name
    components_dir = schematic_dir / "components"
    components_dir.mkdir(parents=True)
    (schematic_dir / "tasks.md").write_text(_TASKS_MD)
    (schematic_dir / "objective.md").write_text(_OBJECTIVE_MD)
    (components_dir / "_overview.md").write_text("# Overview\n")
    (components_dir / "foundation_service.md").write_text("## Contract\ncontent\n")
    (components_dir / "reel_enrichment_service.md").write_text("## Contract\ncontent\n")
    (components_dir / "another_service.md").write_text("## Contract\ncontent\n")
    return schematic_dir


def _make_args(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _with_resolved_dir(schematic_dir: Path, fn: Any, args: Any) -> None:
    with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir):
        fn(args)


def _claim_task(schematic_dir: Path, tag: str) -> None:
    """Move a task pending → in_progress in both tasks.md and the state file."""
    _cli.update_task_status_in_file(schematic_dir / "tasks.md", tag, _cli.TASK_STATUS_IN_PROGRESS)
    state = _cli.load_state(schematic_dir)
    state["tasks"].setdefault(tag, {})["status"] = _cli.TASK_STATUS_IN_PROGRESS
    _cli.save_state(schematic_dir, state)


def _run_task_ask(schematic_dir: Path, tag: str, question: str) -> None:
    args = _make_args(tag=tag, text=question, schematic=schematic_dir.name)
    _with_resolved_dir(schematic_dir, _cli._task_ask, args)


def _run_answer(schematic_dir: Path, question_id: str, answer: str) -> None:
    args = _make_args(id=question_id, text=answer, name=schematic_dir.name)
    with patch.object(_cli, "_resolve_single_or_all", return_value=[schematic_dir]):
        _cli.cmd_answer(args)


def _status_of(schematic_dir: Path, tag: str) -> str:
    return next(
        task["status"]
        for task in _cli.parse_tasks(schematic_dir / "tasks.md")
        if task["tag"] == tag
    )


def _captured_stdout(fn: Any, **kwargs: Any) -> str:
    """Run fn(**kwargs) and return everything it printed."""
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        fn(**kwargs)
    return captured.getvalue()

# ── Fixtures ───────────────────────────────────────────────────────────────────


class TestTaskHeaderRegex(unittest.TestCase):

    def test_parses_valid_tag_fields(self) -> None:
        match = _cli.TASK_HEADER_RE.match("## b.1 | Create | ReelEnrichmentService")
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), "b.1")
        self.assertEqual(match.group(2), "Create")
        self.assertEqual(match.group(3), "ReelEnrichmentService")

    def test_rejects_uppercase_tag_prefix(self) -> None:
        self.assertIsNone(_cli.TASK_HEADER_RE.match("## B.1 | Create | ReelEnrichmentService"))

    def test_rejects_bare_tag_without_action_and_target(self) -> None:
        self.assertIsNone(_cli.TASK_HEADER_RE.match("## b.1"))

    def test_rejects_missing_pipe_separators(self) -> None:
        self.assertIsNone(_cli.TASK_HEADER_RE.match("## b.1 Create ReelEnrichmentService"))

    def test_rejects_non_header_line(self) -> None:
        self.assertIsNone(_cli.TASK_HEADER_RE.match("Status: pending"))


# Fixtures


class TestStateIO(unittest.TestCase):

    def test_load_state_returns_empty_structure_when_no_file_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            loaded_state = _cli.load_state(Path(tmp))
            self.assertEqual(
                loaded_state,
                {
                    "phases": {}, "tasks": {}, "overrides": [],
                    "run": None, "sweeps": [], "milestones": None,
                },
            )

    def test_load_migrates_legacy_state_without_a_milestones_key(self) -> None:
        # Given a state file written before the milestones key existed
        with TemporaryDirectory() as tmp:
            legacy_state = {
                "phases": {"7": {"status": "locked", "signed_off": True}},
                "tasks": {"a.1": {"status": "complete"}},
                "overrides": [],
                "run": None,
                "sweeps": [],
            }
            _cli.save_state(Path(tmp), legacy_state)

            # When loading it
            loaded_state = _cli.load_state(Path(tmp))

            # Then the milestone gate reads as never decided
            self.assertIsNone(loaded_state["milestones"])

    def test_load_migrates_legacy_state_with_run_and_sweeps_keys(self) -> None:
        # Given a state file written before the run/sweeps keys existed
        with TemporaryDirectory() as tmp:
            legacy_state = {
                "phases": {"1": {"status": "locked", "signed_off": True}},
                "tasks": {"a.1": {"status": "complete"}},
                "overrides": [],
            }
            _cli.save_state(Path(tmp), legacy_state)
            # When loading it
            loaded_state = _cli.load_state(Path(tmp))
            # Then the new keys are injected with empty defaults
            self.assertIsNone(loaded_state["run"])
            self.assertEqual(loaded_state["sweeps"], [])

    def test_save_then_load_produces_identical_state(self) -> None:
        with TemporaryDirectory() as tmp:
            original_state = {
                "phases": {"1": {"status": "locked", "signed_off": True}},
                "tasks": {"a.1": {"status": "complete"}},
                "overrides": [],
                "run": None,
                "sweeps": [],
                "milestones": None,
            }
            _cli.save_state(Path(tmp), original_state)
            loaded_state = _cli.load_state(Path(tmp))
            self.assertEqual(loaded_state, original_state)

    def test_record_override_appends_entry_with_required_fields(self) -> None:
        state: dict = {"overrides": []}
        _cli.record_override(state, context="phase complete 3", reason="debugging")
        self.assertEqual(len(state["overrides"]), 1)
        override = state["overrides"][0]
        self.assertEqual(override["context"], "phase complete 3")
        self.assertEqual(override["reason"], "debugging")
        self.assertIn("at", override)

    def test_record_override_accumulates_multiple_entries(self) -> None:
        state: dict = {"overrides": []}
        _cli.record_override(state, context="first", reason="r1")
        _cli.record_override(state, context="second", reason="r2")
        self.assertEqual(len(state["overrides"]), 2)


# Fixtures


class TestParseTasksMd(unittest.TestCase):

    def test_parses_correct_number_of_tasks(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            self.assertEqual(len(tasks), 3)

    def test_parses_status_values_for_each_task(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            tag_to_status = {t["tag"]: t["status"] for t in tasks}
            self.assertEqual(tag_to_status["a.1"], "complete")
            self.assertEqual(tag_to_status["b.1"], "pending")
            self.assertEqual(tag_to_status["b.2"], "pending")

    def test_parses_blocked_by_tags_correctly(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["blocked_by"], ["a.1"])

    def test_parses_component_file_path(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["component_file"], "./components/reel_enrichment_service.md")

    def test_returns_empty_list_when_file_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            tasks = _cli.parse_tasks(Path(tmp) / "nonexistent.md")
            self.assertEqual(tasks, [])

    def test_task_with_no_blockers_has_empty_blocked_by(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            a1_task = next(t for t in tasks if t["tag"] == "a.1")
            self.assertEqual(a1_task["blocked_by"], [])


# Fixtures


class TestUpdateTaskStatusInFile(unittest.TestCase):

    def test_updates_target_task_status_in_place(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            _cli.update_task_status_in_file(tasks_md, "b.1", "in_progress")
            updated_tasks = _cli.parse_tasks(tasks_md)
            b1_task = next(t for t in updated_tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["status"], "in_progress")

    def test_does_not_modify_other_task_statuses(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            _cli.update_task_status_in_file(tasks_md, "b.1", "in_progress")
            updated_tasks = _cli.parse_tasks(tasks_md)
            a1_task = next(t for t in updated_tasks if t["tag"] == "a.1")
            self.assertEqual(a1_task["status"], "complete")

    def test_exits_with_error_when_tag_not_found(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            with self.assertRaises(SystemExit):
                _cli.update_task_status_in_file(schematic_dir / "tasks.md", "z.9", "complete")


# Fixtures


class TestPhaseEnforcement(unittest.TestCase):

    def test_phase_complete_fails_without_audit_for_audit_required_phase(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["1"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)
            args = _make_args(num=1, schematic="test-feature", override=None)
            with self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

    def test_phase_complete_fails_without_signoff(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["1"] = {"audit_result": "clean"}
            _cli.save_state(schematic_dir, state)
            args = _make_args(num=1, schematic="test-feature", override=None)
            with self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

    def test_phase_complete_locks_phase_when_audit_and_signoff_present(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["1"] = {"audit_result": "clean", "signed_off": True}
            _cli.save_state(schematic_dir, state)
            args = _make_args(num=1, schematic="test-feature", override=None)
            _with_resolved_dir(schematic_dir, _cli._phase_complete, args)
            updated_state = _cli.load_state(schematic_dir)
            self.assertEqual(updated_state["phases"]["1"]["status"], "locked")

    def test_phase_complete_locks_with_override_when_both_gates_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            args = _make_args(num=1, schematic="test-feature", override="debugging session")
            _with_resolved_dir(schematic_dir, _cli._phase_complete, args)
            updated_state = _cli.load_state(schematic_dir)
            self.assertEqual(updated_state["phases"]["1"]["status"], "locked")
            self.assertGreaterEqual(len(updated_state["overrides"]), 1)

    def test_phase_3_complete_skips_audit_check(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["3"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)
            args = _make_args(num=3, schematic="test-feature", override=None)
            _with_resolved_dir(schematic_dir, _cli._phase_complete, args)
            updated_state = _cli.load_state(schematic_dir)
            self.assertEqual(updated_state["phases"]["3"]["status"], "locked")

    def test_phase_audit_rejects_non_audit_phase(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            args = _make_args(num=3, result="clean", schematic="test-feature")
            with self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._phase_audit, args)

    def test_phase_9_complete_locks_without_audit(self) -> None:
        # Given phase 9 signed off (compression has no audit hook)
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["9"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)
            # When completing
            args = _make_args(num=9, schematic="test-feature", override=None)
            _with_resolved_dir(schematic_dir, _cli._phase_complete, args)
            # Then phase 9 locks
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["9"]["status"], "locked")

    def test_phase_8_complete_rejects_missing_implementation_report(self) -> None:
        # Given phase 8 signed off but no implementation_report.md on disk
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["8"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)
            # When completing / Then the artifact check rejects
            args = _make_args(num=8, schematic="test-feature", override=None)
            with self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

    def test_phase_5_complete_rejects_invalid_dag_mermaid(self) -> None:
        # Given phase 5 signed off with artifacts on disk but a dag.mmd that fails validation
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "_overview.md").write_text(
                "# Overview\n## Injection DAG\nedges\n## App Integration\nwiring\n"
            )
            (schematic_dir / "dag.mmd").write_text("flowchart TD\nA --> B\n")
            state = _cli.load_state(schematic_dir)
            state["phases"]["5"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)
            # When completing / Then the mermaid check rejects
            args = _make_args(num=5, schematic="test-feature", override=None)
            with patch.object(_cli, "_validate_mermaid_file", return_value=["line 2: bad edge"]), \
                 self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

    def test_phase_5_complete_locks_when_dag_mermaid_valid(self) -> None:
        # Given phase 5 signed off with artifacts on disk and a valid dag.mmd
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "_overview.md").write_text(
                "# Overview\n## Injection DAG\nedges\n## App Integration\nwiring\n"
            )
            (schematic_dir / "dag.mmd").write_text("flowchart TD\nA --> B\n")
            state = _cli.load_state(schematic_dir)
            state["phases"]["5"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)
            # When completing
            args = _make_args(num=5, schematic="test-feature", override=None)
            with patch.object(_cli, "_validate_mermaid_file", return_value=[]):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)
            # Then phase 5 locks
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["5"]["status"], "locked")

    def test_phase_5_complete_locks_with_override_despite_invalid_mermaid(self) -> None:
        # Given phase 5 signed off with artifacts on disk but an invalid dag.mmd
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "_overview.md").write_text(
                "# Overview\n## Injection DAG\nedges\n## App Integration\nwiring\n"
            )
            (schematic_dir / "dag.mmd").write_text("flowchart TD\nA --> B\n")
            state = _cli.load_state(schematic_dir)
            state["phases"]["5"] = {"signed_off": True, "audit_result": "clean"}
            _cli.save_state(schematic_dir, state)
            # When completing with an override
            args = _make_args(num=5, schematic="test-feature", override="diagram fix deferred")
            with patch.object(_cli, "_validate_mermaid_file", return_value=["line 2: bad edge"]):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)
            # Then phase 5 locks and the override is recorded
            updated_state = _cli.load_state(schematic_dir)
            self.assertEqual(updated_state["phases"]["5"]["status"], "locked")
            self.assertGreaterEqual(len(updated_state["overrides"]), 1)


# Fixtures


class TestTaskStatusTransitions(unittest.TestCase):

    def _run_task_status(
        self,
        schematic_dir: Path,
        tag: str,
        new_status: str,
        override: str | None = None,
    ) -> None:
        args = _make_args(
            tag=tag,
            status=new_status,
            schematic=schematic_dir.name,
            override=override,
        )
        _with_resolved_dir(schematic_dir, _cli._task_status, args)

    def test_pending_to_in_progress_updates_tasks_md(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._run_task_status(schematic_dir, "b.1", "in_progress")
            updated_tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in updated_tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["status"], "in_progress")

    def test_pending_to_complete_requires_override(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            with self.assertRaises(SystemExit):
                self._run_task_status(schematic_dir, "b.1", "complete")

    def test_pending_to_complete_succeeds_with_override(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._run_task_status(schematic_dir, "b.1", "complete", override="skipping step")
            updated_tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in updated_tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["status"], "complete")

    def test_complete_to_any_status_requires_override(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            with self.assertRaises(SystemExit):
                self._run_task_status(schematic_dir, "a.1", "pending")

    def test_status_transition_updates_state_file(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._run_task_status(schematic_dir, "b.1", "in_progress")
            state = _cli.load_state(schematic_dir)
            self.assertEqual(state["tasks"]["b.1"]["status"], "in_progress")


# Fixtures


class TestTaskComplete(unittest.TestCase):

    def _run_task_complete(
        self, schematic_dir: Path, tag: str, override: str | None = None
    ) -> None:
        args = _make_args(tag=tag, schematic=schematic_dir.name, override=override)
        _with_resolved_dir(schematic_dir, _cli._task_complete, args)

    def _record_review(self, schematic_dir: Path, tag: str, verdict: str) -> None:
        state = _cli.load_state(schematic_dir)
        state["tasks"].setdefault(tag, {})["review_request"] = {
            "tag": tag,
            "status": verdict,
        }
        _cli.save_state(schematic_dir, state)

    def test_complete_fails_when_task_is_pending(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._record_review(schematic_dir, "b.1", "clean")
            with self.assertRaises(SystemExit):
                self._run_task_complete(schematic_dir, "b.1")

    def test_complete_fails_when_no_review_recorded(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "b.1", "in_progress")
            with self.assertRaises(SystemExit):
                self._run_task_complete(schematic_dir, "b.1")

    def test_complete_fails_when_review_verdict_is_findings(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "b.1", "in_progress")
            self._record_review(schematic_dir, "b.1", "findings")
            with self.assertRaises(SystemExit):
                self._run_task_complete(schematic_dir, "b.1")

    def test_complete_succeeds_when_in_progress_with_clean_review(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "b.1", "in_progress")
            self._record_review(schematic_dir, "b.1", "clean")
            self._run_task_complete(schematic_dir, "b.1")
            updated_tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in updated_tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["status"], "complete")

    def test_complete_succeeds_when_in_review_with_clean_review(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "b.1", "review")
            self._record_review(schematic_dir, "b.1", "clean")
            self._run_task_complete(schematic_dir, "b.1")
            updated_tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in updated_tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["status"], "complete")

    def test_complete_with_override_bypasses_status_and_review_checks(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._run_task_complete(schematic_dir, "b.1", override="fast-tracking")
            updated_tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            b1_task = next(t for t in updated_tasks if t["tag"] == "b.1")
            self.assertEqual(b1_task["status"], "complete")


# Fixtures


class TestTaskReviewResult(unittest.TestCase):

    def _run_review_result(
        self, schematic_dir: Path, tag: str, verdict: str, summary: str
    ) -> None:
        args = _make_args(
            tag=tag,
            verdict=verdict,
            summary=summary,
            schematic=schematic_dir.name,
        )
        _with_resolved_dir(schematic_dir, _cli._task_review_result, args)

    def _request_review(self, schematic_dir: Path, tag: str) -> None:
        state = _cli.load_state(schematic_dir)
        state["tasks"].setdefault(tag, {})["review_request"] = {
            "tag": tag,
            "status": "pending",
        }
        _cli.save_state(schematic_dir, state)

    def test_review_result_fails_without_prior_review_request(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            with self.assertRaises(SystemExit):
                self._run_review_result(schematic_dir, "b.1", "clean", "all good")

    def test_review_result_records_clean_verdict_and_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._request_review(schematic_dir, "b.1")
            self._run_review_result(schematic_dir, "b.1", "clean", "all good")
            review_request = _cli.load_state(schematic_dir)["tasks"]["b.1"]["review_request"]
            self.assertEqual(review_request["status"], "clean")
            self.assertEqual(review_request["summary"], "all good")

    def test_review_result_records_findings_verdict(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._request_review(schematic_dir, "b.1")
            self._run_review_result(schematic_dir, "b.1", "findings", "2 naming violations")
            review_request = _cli.load_state(schematic_dir)["tasks"]["b.1"]["review_request"]
            self.assertEqual(review_request["status"], "findings")


# Fixtures


class TestTaskNext(unittest.TestCase):

    def test_returns_first_unblocked_pending_task(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks = _cli.parse_tasks(schematic_dir / "tasks.md")
            complete_tags = {t["tag"] for t in tasks if t["status"] == "complete"}
            pending_unblocked = [
                t for t in tasks
                if t["status"] == "pending"
                and not [b for b in t["blocked_by"] if b not in complete_tags]
            ]
            self.assertEqual(len(pending_unblocked), 1)
            self.assertEqual(pending_unblocked[0]["tag"], "b.1")

    def test_unblocks_chained_task_when_blocker_completes(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            _cli.update_task_status_in_file(tasks_md, "b.1", "complete")
            tasks = _cli.parse_tasks(tasks_md)
            complete_tags = {t["tag"] for t in tasks if t["status"] == "complete"}
            pending_unblocked = [
                t for t in tasks
                if t["status"] == "pending"
                and not [b for b in t["blocked_by"] if b not in complete_tags]
            ]
            self.assertEqual(len(pending_unblocked), 1)
            self.assertEqual(pending_unblocked[0]["tag"], "b.2")

    def test_returns_no_tasks_when_all_complete(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            _cli.update_task_status_in_file(tasks_md, "b.1", "complete")
            _cli.update_task_status_in_file(tasks_md, "b.2", "complete")
            tasks = _cli.parse_tasks(tasks_md)
            complete_tags = {t["tag"] for t in tasks if t["status"] == "complete"}
            pending_unblocked = [
                t for t in tasks
                if t["status"] == "pending"
                and not [b for b in t["blocked_by"] if b not in complete_tags]
            ]
            self.assertEqual(pending_unblocked, [])


# Fixtures


class TestValidate(unittest.TestCase):

    def test_passes_clean_schematic_with_no_non_override_findings(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            findings = _cli._validate_schematic(schematic_dir)
            non_override_findings = [f for f in findings if "override" not in f]
            self.assertEqual(non_override_findings, [])

    def test_catches_unresolved_blocked_by_tag(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            tasks_md.write_text(
                tasks_md.read_text().replace(
                    "Blocked by: a.1 | Create | FoundationService",
                    "Blocked by: z.9 | Create | GhostService",
                )
            )
            findings = _cli._validate_schematic(schematic_dir)
            self.assertTrue(any("z.9" in f for f in findings))

    def test_catches_missing_component_file(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "reel_enrichment_service.md").unlink()
            findings = _cli._validate_schematic(schematic_dir)
            self.assertTrue(any("reel_enrichment_service" in f for f in findings))

    def test_catches_state_drift_between_tasks_md_and_state_file(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["tasks"]["b.1"] = {"status": "complete"}
            _cli.save_state(schematic_dir, state)
            findings = _cli._validate_schematic(schematic_dir)
            self.assertTrue(any("b.1" in f and "drift" in f for f in findings))

    def test_surfaces_overrides_as_findings(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            _cli.record_override(state, "phase complete 2", "debugging")
            _cli.save_state(schematic_dir, state)
            findings = _cli._validate_schematic(schematic_dir)
            self.assertTrue(any("override" in f for f in findings))

    def test_flags_task_in_pending_input(self) -> None:
        # Given a task held awaiting the user
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When validating
            findings = _cli._validate_schematic(schematic_dir)

            # Then the held task is a finding
            self.assertTrue(any("b.1" in f and "pendingInput" in f for f in findings))

    def test_flags_unanswered_question(self) -> None:
        # Given an unanswered question in the relay
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When validating
            findings = _cli._validate_schematic(schematic_dir)

            # Then the open question is a finding naming its id
            self.assertTrue(any(_TASK_QUESTION_ID_FIRST in f for f in findings))

    def test_clean_when_question_answered_and_task_resumed(self) -> None:
        # Given the question answered and the task back in progress
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _run_answer(schematic_dir, _TASK_QUESTION_ID_FIRST, _ANSWER_KEY_CHOICE)

            # When validating
            findings = _cli._validate_schematic(schematic_dir)

            # Then neither the state nor the question is a finding
            self.assertEqual(
                [f for f in findings if "pendingInput" in f or "question" in f],
                [],
            )


# Fixtures


class TestMermaidHeuristics(unittest.TestCase):

    def _check(self, content: str) -> list[str]:
        with TemporaryDirectory() as tmp:
            mmd_file = Path(tmp) / "test.mmd"
            mmd_file.write_text(content)
            return _cli._heuristic_mermaid_check(mmd_file)

    def test_passes_valid_sequence_diagram(self) -> None:
        self.assertEqual(self._check(_VALID_SEQUENCE_MMD), [])

    def test_catches_missing_sequencediagram_declaration(self) -> None:
        findings = self._check(_SEQUENCE_MISSING_DECL)
        self.assertTrue(any("unrecognised diagram type" in f for f in findings))

    def test_catches_unbalanced_loop_missing_end(self) -> None:
        findings = self._check(_SEQUENCE_UNBALANCED_LOOP)
        self.assertTrue(any("unclosed 'loop'" in f for f in findings))

    def test_catches_invalid_note_syntax(self) -> None:
        findings = self._check(_SEQUENCE_BAD_NOTE)
        self.assertTrue(any("Note" in f and "syntax" in f for f in findings))

    def test_passes_valid_flowchart(self) -> None:
        self.assertEqual(self._check(_VALID_FLOWCHART_MMD), [])

    def test_catches_invalid_flowchart_declaration(self) -> None:
        findings = self._check(_INVALID_FLOWCHART_DECL)
        self.assertTrue(len(findings) > 0)

    def test_returns_error_for_empty_file(self) -> None:
        findings = self._check("  \n  \n")
        self.assertEqual(findings, ["empty file"])


# Fixtures


class TestSetup(unittest.TestCase):

    def test_dry_run_does_not_write_settings(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch.object(_cli, "find_project_root", return_value=Path(tmp)):
                args = _make_args(install=False)
                _cli.cmd_setup(args)
                self.assertFalse((Path(tmp) / ".claude" / "settings.json").exists())

    def test_install_creates_settings_with_hook(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch.object(_cli, "find_project_root", return_value=Path(tmp)):
                args = _make_args(install=True)
                _cli.cmd_setup(args)
                settings_path = Path(tmp) / ".claude" / "settings.json"
                self.assertTrue(settings_path.exists())
                settings = json.loads(settings_path.read_text())
                post_tool_use = settings["hooks"]["PostToolUse"]
                self.assertTrue(len(post_tool_use) == 1)
                command = post_tool_use[0]["hooks"][0]["command"]
                self.assertIn(_cli._HOOK_MARKER, command)

    def test_install_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch.object(_cli, "find_project_root", return_value=Path(tmp)):
                args = _make_args(install=True)
                _cli.cmd_setup(args)
                _cli.cmd_setup(args)
                settings = json.loads((Path(tmp) / ".claude" / "settings.json").read_text())
                hook_count = len(settings["hooks"]["PostToolUse"])
                self.assertEqual(hook_count, 1)

    def test_install_merges_with_existing_settings(self) -> None:
        with TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True)
            settings_path.write_text(json.dumps({"model": "claude-opus-4-7"}) + "\n")
            with patch.object(_cli, "find_project_root", return_value=Path(tmp)):
                _cli.cmd_setup(_make_args(install=True))
                settings = json.loads(settings_path.read_text())
                self.assertEqual(settings["model"], "claude-opus-4-7")
                self.assertIn("hooks", settings)


# Fixtures


class TestMermaidEdgeCases(unittest.TestCase):

    def _check(self, content: str) -> list[str]:
        with TemporaryDirectory() as tmp:
            mmd_file = Path(tmp) / "test.mmd"
            mmd_file.write_text(content)
            return _cli._heuristic_mermaid_check(mmd_file)

    def test_flowchart_subgraph_keyword_does_not_false_positive(self) -> None:
        content = "flowchart TD\nsubgraph RetryLoop [Retry]\nA --> B\nend\n"
        findings = self._check(content)
        self.assertEqual(findings, [])

    def test_flowchart_style_keyword_does_not_false_positive(self) -> None:
        content = "flowchart TD\nA --> B\nstyle A fill:#f9f\n"
        findings = self._check(content)
        self.assertEqual(findings, [])

    def test_known_but_unchecked_diagram_type_passes_cleanly(self) -> None:
        self.assertEqual(self._check("classDiagram\nAnimal <|-- Duck\n"), [])
        self.assertEqual(self._check("erDiagram\nCUSTOMER ||--o{ ORDER : places\n"), [])
        self.assertEqual(self._check("gantt\ntitle Schedule\n"), [])


class TestParseFeatureAcs(unittest.TestCase):

    def test_returns_empty_when_section_heading_absent(self) -> None:
        with TemporaryDirectory() as tmp:
            objective_md = Path(tmp) / "objective.md"
            objective_md.write_text("# Feature\n\n## Context & Objective\nsome content\n")
            result = _cli.parse_feature_acs(objective_md)
            self.assertEqual(result, [])

    def test_returns_empty_when_section_present_but_contains_no_ac_codes(self) -> None:
        with TemporaryDirectory() as tmp:
            objective_md = Path(tmp) / "objective.md"
            objective_md.write_text(
                "# Feature\n\n## Feature Change List + Feature ACs\nPart of change set: something\n"
            )
            result = _cli.parse_feature_acs(objective_md)
            self.assertEqual(result, [])

    def test_extracts_ac_codes_from_section(self) -> None:
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            result = _cli.parse_feature_acs(schematic_dir / "objective.md")
            self.assertIn("1.A", result)


class TestDiffBatching(unittest.TestCase):

    def test_returns_single_batch_when_files_at_max(self) -> None:
        # Given five changed files and a max of five per batch
        changed_files = ["a.py", "b.py", "c.py", "d.py", "e.py"]
        # When sharding
        batches = _cli._shard_diff_into_batches(changed_files, 5)
        # Then one batch holds all five
        self.assertEqual(batches, [["a.py", "b.py", "c.py", "d.py", "e.py"]])

    def test_splits_into_batches_when_over_max(self) -> None:
        # Given twelve files and a max of five
        changed_files = [f"f{index}.py" for index in range(12)]
        # When sharding
        batches = _cli._shard_diff_into_batches(changed_files, 5)
        # Then batch sizes are 5, 5, 2
        self.assertEqual([len(batch) for batch in batches], [5, 5, 2])

    def test_returns_empty_list_when_no_files(self) -> None:
        # Given no changed files / When sharding / Then no batches
        self.assertEqual(_cli._shard_diff_into_batches([], 5), [])

    def test_preserves_file_order_across_batches(self) -> None:
        # Given an ordered list spanning two batches
        changed_files = ["1", "2", "3", "4", "5", "6"]
        # When sharding then flattening
        batches = _cli._shard_diff_into_batches(changed_files, 5)
        flattened = [path for batch in batches for path in batch]
        # Then original order is preserved
        self.assertEqual(flattened, changed_files)

    def test_unions_tracked_and_untracked_diff_files(self) -> None:
        # Given git diff lists two files and ls-files lists one new (with overlap)
        diff_result = _cli.subprocess.CompletedProcess(args=[], returncode=0, stdout="src/b.py\nsrc/a.py\n")
        untracked_result = _cli.subprocess.CompletedProcess(args=[], returncode=0, stdout="src/a.py\nsrc/c.py\n")
        # When collecting the cumulative diff
        with patch.object(_cli.subprocess, "run", side_effect=[diff_result, untracked_result]):
            diff_files = _cli._cumulative_diff_files("BASE", Path("/repo"))
        # Then the union is sorted and deduped
        self.assertEqual(diff_files, ["src/a.py", "src/b.py", "src/c.py"])

    def test_returns_empty_diff_when_no_changes_since_base(self) -> None:
        # Given both git calls return nothing
        empty = _cli.subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        # When collecting the cumulative diff
        with patch.object(_cli.subprocess, "run", side_effect=[empty, empty]):
            diff_files = _cli._cumulative_diff_files("BASE", Path("/repo"))
        # Then there are no files
        self.assertEqual(diff_files, [])

    def test_excludes_schematic_planning_artifacts(self) -> None:
        # Given the diff includes a feature file and the schematic state file
        diff_result = _cli.subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="src/a.py\ndocs/schematics/demo/.schematic-state.json\n",
        )
        untracked_result = _cli.subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        # When collecting the cumulative diff
        with patch.object(_cli.subprocess, "run", side_effect=[diff_result, untracked_result]):
            diff_files = _cli._cumulative_diff_files("BASE", Path("/repo"))
        # Then only the feature file remains
        self.assertEqual(diff_files, ["src/a.py"])


class TestReviewStart(unittest.TestCase):

    def _run_start(self, schematic_dir: Path, auto: bool, goal: str | None) -> None:
        args = _make_args(schematic=schematic_dir.name, auto=auto, goal=goal)
        with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
             patch.object(_cli, "find_project_root", return_value=schematic_dir), \
             patch.object(_cli, "_run_git", return_value=["abc123def456"]):
            _cli._review_start(args)

    def test_records_auto_mode_and_base_ref(self) -> None:
        # Given an auto run with a goal
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            # When starting
            self._run_start(schematic_dir, auto=True, goal="ship reels")
            # Then mode, goal and base_ref are recorded
            run = _cli.load_state(schematic_dir)["run"]
            self.assertEqual(run["mode"], "auto")
            self.assertEqual(run["goal"], "ship reels")
            self.assertEqual(run["base_ref"], "abc123def456")

    def test_exits_when_auto_without_goal(self) -> None:
        # Given auto mode and no goal / When starting / Then it exits
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            with self.assertRaises(SystemExit):
                self._run_start(schematic_dir, auto=True, goal=None)

    def test_records_manual_mode_without_goal(self) -> None:
        # Given manual mode with no goal
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            # When starting
            self._run_start(schematic_dir, auto=False, goal=None)
            # Then mode is manual
            self.assertEqual(_cli.load_state(schematic_dir)["run"]["mode"], "manual")


class TestReviewSweep(unittest.TestCase):

    def _seed_run(self, schematic_dir: Path) -> None:
        state = _cli.load_state(schematic_dir)
        state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
        _cli.save_state(schematic_dir, state)

    def _run_sweep(self, schematic_dir: Path, diff_files: list[str]) -> None:
        args = _make_args(schematic=schematic_dir.name)
        with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
             patch.object(_cli, "find_project_root", return_value=schematic_dir), \
             patch.object(_cli, "_cumulative_diff_files", return_value=diff_files), \
             patch.object(_cli, "_run_git_raw", return_value=""):
            _cli._review_sweep(args)

    def test_appends_sweep_with_sharded_batches(self) -> None:
        # Given seven changed files and an auto run
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run(schematic_dir)
            # When sweeping
            self._run_sweep(schematic_dir, [f"src/f{index}.py" for index in range(7)])
            # Then one sweep with two batches (5, 2) and sequential ids is recorded
            sweep = _cli.load_state(schematic_dir)["sweeps"][0]
            self.assertEqual(sweep["sweep_id"], 1)
            self.assertEqual([len(b["files"]) for b in sweep["batches"]], [5, 2])
            self.assertEqual([b["batch_id"] for b in sweep["batches"]], ["1.1", "1.2"])

    def test_exits_when_no_auto_run_recorded(self) -> None:
        # Given no run / When sweeping / Then it exits
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            with self.assertRaises(SystemExit):
                self._run_sweep(schematic_dir, ["src/a.py"])

    def test_exits_when_no_changes_since_base(self) -> None:
        # Given an auto run but an empty diff / When sweeping / Then it exits
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run(schematic_dir)
            with self.assertRaises(SystemExit):
                self._run_sweep(schematic_dir, [])

    def test_sweep_stamps_the_open_milestone_on_the_sweep_record(self) -> None:
        # Given locked milestones with M1 open
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._seed_run(schematic_dir)

            # When sweeping
            self._run_sweep(schematic_dir, ["src/a.py"])

            # Then the sweep records which milestone it covered
            self.assertEqual(_cli.load_state(schematic_dir)["sweeps"][0]["milestone"], "M1")

    def test_sweep_stamps_no_milestone_when_none_are_declared(self) -> None:
        # Given a bundle with no Milestones table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run(schematic_dir)

            # When sweeping
            self._run_sweep(schematic_dir, ["src/a.py"])

            # Then the sweep is stamped with nothing
            self.assertIsNone(_cli.load_state(schematic_dir)["sweeps"][0]["milestone"])


class TestReviewSweepIncremental(unittest.TestCase):

    def _seed_run(self, schematic_dir: Path) -> None:
        state = _cli.load_state(schematic_dir)
        state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
        _cli.save_state(schematic_dir, state)

    def _seed_clean_sweep(self, schematic_dir: Path, path_to_diff: dict[str, str]) -> None:
        state = _cli.load_state(schematic_dir)
        state["sweeps"] = [{
            "sweep_id": 1,
            "batches": [{
                "batch_id": "1.1",
                "files": sorted(path_to_diff),
                "file_hashes": {p: _cli._diff_hash(d) for p, d in path_to_diff.items()},
                "verdict": "clean",
                "summary": "ok",
            }],
            "pristine": True,
        }]
        _cli.save_state(schematic_dir, state)

    def _run_sweep(self, schematic_dir: Path, path_to_diff: dict[str, str]) -> None:
        args = _make_args(schematic=schematic_dir.name)
        with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
             patch.object(_cli, "find_project_root", return_value=schematic_dir), \
             patch.object(_cli, "_cumulative_diff_files", return_value=sorted(path_to_diff)), \
             patch.object(_cli, "_file_diff", side_effect=lambda p, ref, root: path_to_diff[p]):
            _cli._review_sweep(args)

    def test_resweep_is_pristine_when_every_file_already_reviewed_clean(self) -> None:
        # Given a prior clean sweep over the exact same per-file diffs
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run(schematic_dir)
            path_to_diff = {"src/a.py": "+a", "src/b.py": "+b"}
            self._seed_clean_sweep(schematic_dir, path_to_diff)
            # When re-sweeping with nothing re-touched
            self._run_sweep(schematic_dir, path_to_diff)
            # Then the new sweep is pristine with zero batches and all files skipped
            resweep = _cli.load_state(schematic_dir)["sweeps"][1]
            self.assertTrue(resweep["pristine"])
            self.assertEqual(resweep["batches"], [])
            self.assertEqual(resweep["skipped_clean"], ["src/a.py", "src/b.py"])

    def test_resweep_batches_only_retouched_files(self) -> None:
        # Given a prior clean sweep, then one file re-touched
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run(schematic_dir)
            self._seed_clean_sweep(schematic_dir, {"src/a.py": "+a", "src/b.py": "+b"})
            # When re-sweeping with b.py changed
            self._run_sweep(schematic_dir, {"src/a.py": "+a", "src/b.py": "+b2"})
            # Then only b.py re-enters a batch and a.py is skipped
            resweep = _cli.load_state(schematic_dir)["sweeps"][1]
            self.assertEqual([b["files"] for b in resweep["batches"]], [["src/b.py"]])
            self.assertEqual(resweep["skipped_clean"], ["src/a.py"])

    def test_findings_batch_files_are_reviewed_again(self) -> None:
        # Given a prior sweep whose only batch had findings
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run(schematic_dir)
            path_to_diff = {"src/a.py": "+a"}
            self._seed_clean_sweep(schematic_dir, path_to_diff)
            state = _cli.load_state(schematic_dir)
            state["sweeps"][0]["batches"][0]["verdict"] = "findings"
            state["sweeps"][0]["pristine"] = False
            _cli.save_state(schematic_dir, state)
            # When re-sweeping with the identical diff
            self._run_sweep(schematic_dir, path_to_diff)
            # Then the file is reviewed again (findings never earn a skip)
            resweep = _cli.load_state(schematic_dir)["sweeps"][1]
            self.assertEqual([b["files"] for b in resweep["batches"]], [["src/a.py"]])


class TestLogicLineCount(unittest.TestCase):
    """_logic_line_count — physical lines minus the lines imports occupy."""

    def test_excludes_single_line_imports(self) -> None:
        # Given a module with three import lines and two code lines
        python_source = (
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "x = 1\n"
            "y = 2\n"
        )

        # When counting logic lines
        logic_line_count = _cli._logic_line_count(python_source=python_source)

        # Then the three import lines are excluded
        assert logic_line_count == 2

    def test_excludes_a_multiline_import(self) -> None:
        # Given a parenthesised import spanning four lines plus one code line
        python_source = (
            "from pkg import (\n"
            "    a,\n"
            "    b,\n"
            ")\n"
            "z = a\n"
        )

        # When counting logic lines
        logic_line_count = _cli._logic_line_count(python_source=python_source)

        # Then every line of the multiline import is excluded
        assert logic_line_count == 1

    def test_counts_blanks_and_docstrings_as_logic(self) -> None:
        # Given a module docstring, a blank line, one import, and one code line
        python_source = (
            '"""Module doc."""\n'
            "\n"
            "import os\n"
            "value = os.getcwd()\n"
        )

        # When counting logic lines
        logic_line_count = _cli._logic_line_count(python_source=python_source)

        # Then only the import is excluded — docstring and blank still count
        assert logic_line_count == 3


class TestResolveMaxFileLines(unittest.TestCase):
    """_resolve_max_file_lines — manifest override, else the packaged default."""

    def test_uses_the_manifest_override_when_present(self) -> None:
        # Given a manifest setting schematic.maxFileLines
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_manifest(
                tmp,
                manifest={"schematic": {"maxFileLines": 50}},
            )

            # When resolving the ceiling
            max_file_lines = _cli._resolve_max_file_lines(project_root=project_root)

            # Then the override wins
            assert max_file_lines == 50

    def test_falls_back_to_the_default_when_unset(self) -> None:
        # Given a manifest with no maxFileLines key
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_manifest(
                tmp,
                manifest={"schematic": {}},
            )

            # When resolving the ceiling
            max_file_lines = _cli._resolve_max_file_lines(project_root=project_root)

            # Then the packaged default applies
            assert max_file_lines == _cli.MAX_FILE_LINES_DEFAULT


class TestOversizedFeatureFiles(unittest.TestCase):
    """_oversized_feature_files — python files over the logic-line ceiling."""

    def _write_python_file(self, project_root: Path, path: str, logic_line_count: int) -> None:
        file_path = project_root / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(
            f"line_{index} = {index}"
            for index in range(logic_line_count)
        )
        file_path.write_text(f"{body}\n")

    def test_flags_a_python_file_over_the_ceiling(self) -> None:
        # Given a python file of twelve logic lines and a ceiling of ten
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            self._write_python_file(project_root, "src/big.py", 12)

            # When scanning
            path_to_logic_lines = _cli._oversized_feature_files(
                diff_files=["src/big.py"],
                project_root=project_root,
                max_file_lines=10,
            )

            # Then the file is flagged with its count
            assert path_to_logic_lines == {"src/big.py": 12}

    def test_keeps_a_file_at_the_ceiling_out(self) -> None:
        # Given a python file exactly at the ceiling
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            self._write_python_file(project_root, "src/exact.py", 10)

            # When scanning with a ceiling of ten
            path_to_logic_lines = _cli._oversized_feature_files(
                diff_files=["src/exact.py"],
                project_root=project_root,
                max_file_lines=10,
            )

            # Then it is not flagged — the ceiling is strict
            assert path_to_logic_lines == {}

    def test_ignores_non_python_files(self) -> None:
        # Given an oversized SQL file
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            self._write_python_file(project_root, "migrations/big.sql", 20)

            # When scanning with a ceiling of ten
            path_to_logic_lines = _cli._oversized_feature_files(
                diff_files=["migrations/big.sql"],
                project_root=project_root,
                max_file_lines=10,
            )

            # Then only python files are measured
            assert path_to_logic_lines == {}

    def test_skips_a_deleted_file(self) -> None:
        # Given a diff path with no working-tree file (a deletion)
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)

            # When scanning
            path_to_logic_lines = _cli._oversized_feature_files(
                diff_files=["src/gone.py"],
                project_root=project_root,
                max_file_lines=10,
            )

            # Then the missing file is skipped, not read
            assert path_to_logic_lines == {}


class TestReviewE2e(unittest.TestCase):
    """_review_e2e — adversarial per-entry-point tracing brief, never a silent auto-fix."""

    def _seed_ready_for_e2e(self, schematic_dir: Path) -> None:
        state = _cli.load_state(schematic_dir)
        state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
        state["sweeps"] = [
            {
                "sweep_id": 1,
                "batches": [],
                "pristine": True,
                "skipped_clean": [],
            },
        ]
        state["consistency"] = {"status": "clean", "verdict": "clean", "summary": "ok"}
        _cli.save_state(schematic_dir, state)

    def _captured_e2e(self, schematic_dir: Path, diff_files: list[str]) -> str:
        args = _make_args(schematic=schematic_dir.name)
        captured = io.StringIO()
        with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
             patch.object(_cli, "find_project_root", return_value=schematic_dir), \
             patch.object(_cli, "_cumulative_diff_files", return_value=diff_files), \
             contextlib.redirect_stdout(captured):
            _cli._review_e2e(args)
        return captured.getvalue()

    def test_brief_asks_for_per_entry_point_tracing(self) -> None:
        # Given an auto run ready for e2e (pristine sweep + clean consistency)
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_ready_for_e2e(schematic_dir)

            # When opening the e2e gate
            e2e_output = self._captured_e2e(schematic_dir, ["src/a.py"])

            # Then the brief orchestrates per-entry-point tracing, not a single master review
            assert "entry-point tracing" in e2e_output
            assert "reviewer PER entry point" in e2e_output
            assert "reconciler" in e2e_output
            assert "MASTER AGENT" not in e2e_output

    def test_brief_forbids_auto_fixing_findings(self) -> None:
        # Given an auto run ready for e2e
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_ready_for_e2e(schematic_dir)

            # When opening the e2e gate
            e2e_output = self._captured_e2e(schematic_dir, ["src/a.py"])

            # Then findings are user-dispositioned, never silently fixed
            assert "USER-DISPOSITIONED, never auto-fixed" in e2e_output
            assert "fix any findings silently" not in e2e_output

    def test_exits_without_a_clean_consistency_gate(self) -> None:
        # Given an auto run with a pristine sweep but no consistency verdict
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
            state["sweeps"] = [{"sweep_id": 1, "batches": [], "pristine": True, "skipped_clean": []}]
            _cli.save_state(schematic_dir, state)

            # When opening the e2e gate / Then it refuses
            with self.assertRaises(SystemExit):
                self._captured_e2e(schematic_dir, ["src/a.py"])

    def test_exits_when_consistency_returned_findings(self) -> None:
        # Given a pristine sweep and a consistency gate that returned findings
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
            state["sweeps"] = [{"sweep_id": 1, "batches": [], "pristine": True, "skipped_clean": []}]
            state["consistency"] = {"status": "findings", "verdict": "findings", "summary": "dup found"}
            _cli.save_state(schematic_dir, state)

            # When opening the e2e gate / Then it refuses — consistency is not clean
            with self.assertRaises(SystemExit):
                self._captured_e2e(schematic_dir, ["src/a.py"])


class TestReviewConsistency(unittest.TestCase):
    """_review_consistency — single-agent whole-diff duplication/redundancy + line-limit, one pass."""

    def _seed_run_and_pristine_sweep(self, schematic_dir: Path) -> None:
        state = _cli.load_state(schematic_dir)
        state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
        state["sweeps"] = [{"sweep_id": 1, "batches": [], "pristine": True, "skipped_clean": []}]
        _cli.save_state(schematic_dir, state)

    def _captured_consistency(self, schematic_dir: Path, diff_files: list[str]) -> str:
        args = _make_args(schematic=schematic_dir.name)
        captured = io.StringIO()
        with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
             patch.object(_cli, "find_project_root", return_value=schematic_dir), \
             patch.object(_cli, "_cumulative_diff_files", return_value=diff_files), \
             patch.object(_cli, "_run_git_raw", return_value=""), \
             contextlib.redirect_stdout(captured):
            _cli._review_consistency(args)
        return captured.getvalue()

    def test_prompt_asks_for_duplication_not_standards(self) -> None:
        # Given an auto run with a pristine sweep
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run_and_pristine_sweep(schematic_dir)

            # When opening the consistency gate
            consistency_output = self._captured_consistency(schematic_dir, ["src/a.py"])

            # Then it asks for duplication in a single view, never a standards re-review
            assert "DUPLICATION" in consistency_output
            assert "single view" in consistency_output
            assert "STYLE + STANDARDS" not in consistency_output

    def test_warns_about_a_file_over_the_line_ceiling(self) -> None:
        # Given a python file well over the default ceiling
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run_and_pristine_sweep(schematic_dir)
            big_body = "\n".join(
                f"line_{index} = {index}"
                for index in range(_cli.MAX_FILE_LINES_DEFAULT + 5)
            )
            big_file = schematic_dir / "src" / "big.py"
            big_file.parent.mkdir(parents=True, exist_ok=True)
            big_file.write_text(f"{big_body}\n")

            # When opening the consistency gate
            consistency_output = self._captured_consistency(schematic_dir, ["src/big.py"])

            # Then the oversized warning names the file
            assert "logic-line" in consistency_output
            assert "src/big.py" in consistency_output

    def test_exits_without_a_pristine_sweep(self) -> None:
        # Given an auto run but no pristine sweep
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
            _cli.save_state(schematic_dir, state)

            # When opening the consistency gate / Then it refuses
            with self.assertRaises(SystemExit):
                self._captured_consistency(schematic_dir, ["src/a.py"])

    def test_exits_when_the_latest_sweep_is_not_pristine(self) -> None:
        # Given an earlier pristine sweep but a later group sweep with outstanding findings
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["run"] = {"mode": "auto", "goal": "g", "base_ref": "BASE", "started_at": "t"}
            state["sweeps"] = [
                {"sweep_id": 1, "batches": [], "pristine": True, "skipped_clean": []},
                {
                    "sweep_id": 2,
                    "batches": [{"batch_id": "2.1", "files": ["src/b.py"], "verdict": "findings", "summary": None}],
                    "pristine": False,
                    "skipped_clean": [],
                },
            ]
            _cli.save_state(schematic_dir, state)

            # When opening the consistency gate / Then it refuses — the latest sweep is not pristine
            with self.assertRaises(SystemExit):
                self._captured_consistency(schematic_dir, ["src/b.py"])

    def test_records_a_clean_verdict(self) -> None:
        # Given a consistency gate opened over one file
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_run_and_pristine_sweep(schematic_dir)
            self._captured_consistency(schematic_dir, ["src/a.py"])

            # When recording a clean verdict
            args = _make_args(verdict="clean", summary="no duplication", schematic=schematic_dir.name)
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
                 contextlib.redirect_stdout(io.StringIO()):
                _cli._review_consistency_result(args)

            # Then the verdict is recorded on the consistency gate
            consistency = _cli.load_state(schematic_dir)["consistency"]
            assert consistency["verdict"] == "clean"


class TestStatusOutput(unittest.TestCase):

    def _captured_status(self, schematic_dir: Path) -> str:
        return _captured_stdout(_cli._print_status, schematic_dir=schematic_dir)

    def test_status_shows_next_phase_over_nine_and_locked_line(self) -> None:
        # Given phases 1-3 locked
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            for phase_num in ("1", "2", "3"):
                state["phases"][phase_num] = {"status": "locked"}
            _cli.save_state(schematic_dir, state)
            # When printing status
            status_output = self._captured_status(schematic_dir)
            # Then the current phase is 4/9 and the locked line is paste-ready
            self.assertIn("phase:     4/9", status_output)
            self.assertIn("locked:    P1 ✓  P2 ✓  P3 ✓", status_output)

    def test_status_shows_complete_when_phase_nine_locked(self) -> None:
        # Given phase 9 locked
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"]["9"] = {"status": "locked"}
            _cli.save_state(schematic_dir, state)
            # When printing status
            status_output = self._captured_status(schematic_dir)
            # Then the schematic reads complete
            self.assertIn("phase:     complete", status_output)

    def test_status_lists_pending_input_tasks_with_count(self) -> None:
        # Given a task held awaiting the user
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When printing status
            status_output = self._captured_status(schematic_dir)

            # Then the held task is counted and named on its own line
            self.assertIn("pendingInput  1  [b.1]", status_output)

    def test_status_shows_dash_when_nothing_locked(self) -> None:
        # Given no locked phases
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            # When printing status
            status_output = self._captured_status(schematic_dir)
            # Then the locked line shows a dash placeholder
            self.assertIn("phase:     1/9", status_output)
            self.assertIn("locked:    —", status_output)


class TestDashboardQuestions(unittest.TestCase):

    def _seed_questions(self, schematic_dir: Path, stem: str, questions: list[dict],
                        answers: list[dict] | None = None, requests: list[dict] | None = None) -> None:
        (schematic_dir / f"{stem}.questions.json").write_text(json.dumps(questions))
        if answers is not None:
            (schematic_dir / f"{stem}.answers.json").write_text(json.dumps(answers))
        if requests is not None:
            (schematic_dir / f"{stem}.agent-requests.json").write_text(json.dumps(requests))

    def test_pending_questions_lists_only_unanswered(self) -> None:
        # Given two questions, one already answered
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_questions(
                schematic_dir, "overview",
                questions=[{"idx": 0, "text": "answered one"}, {"idx": 1, "text": "open one"}],
                answers=[{"idx": 0, "answer": "done"}],
                requests=[{"idx": 1, "question": "open one", "prompt": "full ctx prompt"}],
            )
            # When collecting pending questions
            pending = _cli._pending_questions(schematic_dir)
            # Then only the unanswered question surfaces, with its compiled prompt
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["id"], "overview#1")
            self.assertEqual(pending[0]["text"], "open one")
            self.assertEqual(pending[0]["prompt"], "full ctx prompt")

    def test_pending_questions_uses_latest_user_thread_message(self) -> None:
        # Given a threaded question
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_questions(
                schematic_dir, "sequence",
                questions=[{"server_idx": 0, "thread": [
                    {"role": "user", "text": "first ask"},
                    {"role": "agent", "text": "partial"},
                    {"role": "user", "text": "follow-up"},
                ]}],
            )
            # When collecting pending questions
            pending = _cli._pending_questions(schematic_dir)
            # Then the latest user message is the surfaced text
            self.assertEqual(pending[0]["text"], "follow-up")

    def test_answer_appends_to_answers_file(self) -> None:
        # Given an unanswered question
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_questions(schematic_dir, "overview", questions=[{"idx": 0, "text": "q"}])
            # When answering it
            args = _make_args(id="overview#0", text="the reply", name=schematic_dir.name)
            with patch.object(_cli, "_resolve_single_or_all", return_value=[schematic_dir]):
                _cli.cmd_answer(args)
            # Then the answer lands in the answers file the UI polls
            answers = json.loads((schematic_dir / "overview.answers.json").read_text())
            self.assertEqual(answers, [{"idx": 0, "answer": "the reply"}])

    def test_answer_rejects_malformed_id(self) -> None:
        # Given an id without the <source>#<idx> shape / When answering / Then it exits
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            args = _make_args(id="overview-0", text="reply", name=schematic_dir.name)
            with patch.object(_cli, "_resolve_single_or_all", return_value=[schematic_dir]), \
                 self.assertRaises(SystemExit):
                _cli.cmd_answer(args)


class TestReviewBatchResult(unittest.TestCase):

    def _seed_sweep(self, schematic_dir: Path) -> None:
        state = _cli.load_state(schematic_dir)
        state["sweeps"] = [{
            "sweep_id": 1,
            "batches": [
                {"batch_id": "1.1", "files": ["a.py"], "verdict": "pending", "summary": None},
                {"batch_id": "1.2", "files": ["b.py"], "verdict": "pending", "summary": None},
            ],
            "pristine": False,
        }]
        _cli.save_state(schematic_dir, state)

    def _run_result(self, schematic_dir: Path, batch_id: str, verdict: str, summary: str) -> None:
        args = _make_args(batch_id=batch_id, verdict=verdict, summary=summary, schematic=schematic_dir.name)
        _with_resolved_dir(schematic_dir, _cli._review_batch_result, args)

    def test_marks_sweep_pristine_when_all_batches_clean(self) -> None:
        # Given a two-batch sweep
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_sweep(schematic_dir)
            # When both batches are recorded clean
            self._run_result(schematic_dir, "1.1", "clean", "ok")
            self._run_result(schematic_dir, "1.2", "clean", "ok")
            # Then the sweep is pristine
            self.assertTrue(_cli.load_state(schematic_dir)["sweeps"][0]["pristine"])

    def test_not_pristine_while_a_batch_has_findings(self) -> None:
        # Given a two-batch sweep
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_sweep(schematic_dir)
            # When one batch is clean and one has findings
            self._run_result(schematic_dir, "1.1", "clean", "ok")
            self._run_result(schematic_dir, "1.2", "findings", "1 naming issue")
            # Then the sweep is not pristine
            self.assertFalse(_cli.load_state(schematic_dir)["sweeps"][0]["pristine"])

    def test_exits_when_batch_id_unknown(self) -> None:
        # Given a sweep without batch 9.9 / When recording it / Then it exits
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_sweep(schematic_dir)
            with self.assertRaises(SystemExit):
                self._run_result(schematic_dir, "9.9", "clean", "ok")


# Fixtures


# Fixtures:

_QUESTION_KEY_CHOICE = "which cache key does the diff window use?"
_QUESTION_STAMP_RULE = "do degenerate rows get a stamp?"
_ANSWER_KEY_CHOICE = "use the anchor polled_at"
_TASK_QUESTION_ID_FIRST = "tasks#0"
_TASK_QUESTION_ID_SECOND = "tasks#1"
_DASHBOARD_QUESTION_ID = "overview#0"


class TestTaskAsk(unittest.TestCase):

    def test_ask_moves_task_to_pending_input_and_files_the_question(self) -> None:
        # Given a claimed task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")

            # When the agent asks a question it cannot answer
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # Then the task is held in pendingInput and the question is filed against it
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pendingInput")
            self.assertEqual(
                _cli.load_state(schematic_dir)["tasks"]["b.1"]["status"],
                "pendingInput",
            )
            questions = json.loads((schematic_dir / "tasks.questions.json").read_text())
            self.assertEqual(
                questions,
                [{"idx": 0, "tag": "b.1", "text": _QUESTION_KEY_CHOICE, "context": "task b.1"}],
            )

    def test_ask_question_surfaces_in_the_pending_relay(self) -> None:
        # Given a filed task question
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When the relay is drained
            pending = _cli._pending_questions(schematic_dir)

            # Then `schematic questions` sees it under the tasks source
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["id"], _TASK_QUESTION_ID_FIRST)
            self.assertEqual(pending[0]["text"], _QUESTION_KEY_CHOICE)

    def test_ask_when_task_is_pending_is_refused(self) -> None:
        # Given an unclaimed task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # Then asking is refused
            with self.assertRaises(SystemExit):
                # When asking before claiming
                _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pending")

    def test_ask_when_task_unknown_is_refused(self) -> None:
        # Given a tag that is not in tasks.md
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # Then asking is refused
            with self.assertRaises(SystemExit):
                # When asking against it
                _run_task_ask(schematic_dir, "z.9", _QUESTION_KEY_CHOICE)

    def test_second_ask_appends_without_dropping_the_first(self) -> None:
        # Given one question already filed on a task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When a second question is asked
            _run_task_ask(schematic_dir, "b.1", _QUESTION_STAMP_RULE)

            # Then both are open, in order
            pending = _cli._pending_questions(schematic_dir)
            self.assertEqual(
                [(question["id"], question["text"]) for question in pending],
                [
                    (_TASK_QUESTION_ID_FIRST, _QUESTION_KEY_CHOICE),
                    (_TASK_QUESTION_ID_SECOND, _QUESTION_STAMP_RULE),
                ],
            )


# Fixtures


class TestAnswerRoundTrip(unittest.TestCase):

    def test_answer_returns_task_to_in_progress(self) -> None:
        # Given a task held in pendingInput by one question
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When the user answers it
            _run_answer(schematic_dir, _TASK_QUESTION_ID_FIRST, _ANSWER_KEY_CHOICE)

            # Then the task resumes and the answer is on file
            self.assertEqual(_status_of(schematic_dir, "b.1"), "in_progress")
            self.assertEqual(
                _cli.load_state(schematic_dir)["tasks"]["b.1"]["status"],
                "in_progress",
            )
            answers = json.loads((schematic_dir / "tasks.answers.json").read_text())
            self.assertEqual(answers, [{"idx": 0, "answer": _ANSWER_KEY_CHOICE}])

    def test_answer_leaves_task_pending_input_while_another_question_is_open(self) -> None:
        # Given two open questions on one task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _run_task_ask(schematic_dir, "b.1", _QUESTION_STAMP_RULE)

            # When only the first is answered
            _run_answer(schematic_dir, _TASK_QUESTION_ID_FIRST, _ANSWER_KEY_CHOICE)

            # Then the task is still held
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pendingInput")

    def test_answer_to_a_dashboard_question_does_not_touch_task_status(self) -> None:
        # Given a claimed task and an unrelated dashboard question
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            (schematic_dir / "overview.questions.json").write_text(
                json.dumps([{"idx": 0, "text": "why this DAG edge?"}])
            )

            # When the dashboard question is answered
            _run_answer(schematic_dir, _DASHBOARD_QUESTION_ID, "it is the write path")

            # Then no task status moves
            self.assertEqual(_status_of(schematic_dir, "b.1"), "in_progress")


# Fixtures


class TestPendingInputGates(unittest.TestCase):

    def _record_clean_review(self, schematic_dir: Path, tag: str) -> None:
        state = _cli.load_state(schematic_dir)
        state["tasks"].setdefault(tag, {})["review_request"] = {"tag": tag, "status": "clean"}
        _cli.save_state(schematic_dir, state)

    def _run_task_complete(self, schematic_dir: Path, tag: str, override: str | None) -> None:
        args = _make_args(tag=tag, schematic=schematic_dir.name, override=override)
        _with_resolved_dir(schematic_dir, _cli._task_complete, args)

    def _run_task_status(self, schematic_dir: Path, tag: str, new_status: str) -> None:
        args = _make_args(
            tag=tag,
            status=new_status,
            schematic=schematic_dir.name,
            override=None,
        )
        _with_resolved_dir(schematic_dir, _cli._task_status, args)

    def test_complete_refused_when_task_is_pending_input(self) -> None:
        # Given a task held in pendingInput that already has a clean review
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            self._record_clean_review(schematic_dir, "b.1")

            # Then completion is refused
            with self.assertRaises(SystemExit):
                # When completing
                self._run_task_complete(schematic_dir, "b.1", override=None)
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pendingInput")

    def test_complete_refused_when_question_unanswered_despite_clean_review(self) -> None:
        # Given a task returned to in_progress by hand while its question is still open
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _claim_task(schematic_dir, "b.1")
            self._record_clean_review(schematic_dir, "b.1")

            # Then completion is refused
            with self.assertRaises(SystemExit):
                # When completing
                self._run_task_complete(schematic_dir, "b.1", override=None)

    def test_complete_refused_with_override_when_question_unanswered(self) -> None:
        # Given the same task and an override reason
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _claim_task(schematic_dir, "b.1")
            self._record_clean_review(schematic_dir, "b.1")

            # Then the override does not unlock an open question
            with self.assertRaises(SystemExit):
                # When completing with an override
                self._run_task_complete(schematic_dir, "b.1", override="shipping tonight")

    def test_complete_allowed_once_the_question_is_answered(self) -> None:
        # Given the question answered and the task resumed
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _run_answer(schematic_dir, _TASK_QUESTION_ID_FIRST, _ANSWER_KEY_CHOICE)
            self._record_clean_review(schematic_dir, "b.1")

            # When completing
            self._run_task_complete(schematic_dir, "b.1", override=None)

            # Then the task completes
            self.assertEqual(_status_of(schematic_dir, "b.1"), "complete")

    def test_status_review_refused_when_question_unanswered(self) -> None:
        # Given a task with an open question, put back in_progress
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _claim_task(schematic_dir, "b.1")

            # Then submitting it for review is refused
            with self.assertRaises(SystemExit):
                # When submitting for review
                self._run_task_status(schematic_dir, "b.1", "review")
            self.assertEqual(_status_of(schematic_dir, "b.1"), "in_progress")

    def test_status_review_allowed_once_the_question_is_answered(self) -> None:
        # Given the question answered
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _run_answer(schematic_dir, _TASK_QUESTION_ID_FIRST, _ANSWER_KEY_CHOICE)

            # When submitting for review
            self._run_task_status(schematic_dir, "b.1", "review")

            # Then the task moves to review
            self.assertEqual(_status_of(schematic_dir, "b.1"), "review")


# Fixtures


class TestTaskDecision(unittest.TestCase):

    def _run_decision(self, schematic_dir: Path, tag: str, kind: str, text: str) -> None:
        args = _make_args(tag=tag, text=text, kind=kind, schematic=schematic_dir.name)
        _with_resolved_dir(schematic_dir, _cli._task_decision, args)

    def test_decision_with_naming_kind_is_recorded(self) -> None:
        # Given a claimed task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # When a naming decision is recorded
            self._run_decision(schematic_dir, "b.1", "naming", "called it anchor_polled_at")

            # Then the ledger holds it with its kind
            decisions = _cli.load_state(schematic_dir)["tasks"]["b.1"]["decisions"]
            self.assertEqual(len(decisions), 1)
            self.assertEqual(decisions[0]["text"], "called it anchor_polled_at")
            self.assertEqual(decisions[0]["kind"], "naming")

    def test_decision_with_placement_kind_is_recorded(self) -> None:
        # Given a claimed task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # When a placement decision is recorded
            self._run_decision(schematic_dir, "b.1", "placement", "put it under utils/")

            # Then the ledger holds it with its kind
            decisions = _cli.load_state(schematic_dir)["tasks"]["b.1"]["decisions"]
            self.assertEqual(decisions[0]["kind"], "placement")

    def test_decision_with_contract_kind_is_refused_pointing_at_task_ask(self) -> None:
        # Given a decision that changes a signed contract
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            captured_error = io.StringIO()

            # Then it is refused and redirected to task ask
            with contextlib.redirect_stderr(captured_error), self.assertRaises(SystemExit):
                # When recording it as a decision
                self._run_decision(schematic_dir, "b.1", "contract", "widened the CHECK")
            self.assertIn("task ask", captured_error.getvalue())
            self.assertEqual(_cli.load_state(schematic_dir)["tasks"], {})


# Fixtures


class TestRatificationPhraseLint(unittest.TestCase):

    def _phrase_findings(self, schematic_dir: Path) -> list[str]:
        return [
            finding for finding in _cli._validate_schematic(schematic_dir)
            if "a note is not a state" in finding
        ]

    def test_flags_open_for_ratification_in_a_component_card(self) -> None:
        # Given a card carrying the phrase and no question filed for its task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "reel_enrichment_service.md").write_text(
                "## Contract\nOPEN FOR RATIFICATION — the window rule may be wrong.\n"
            )

            # When validating
            findings = self._phrase_findings(schematic_dir)

            # Then the card is flagged
            self.assertTrue(any("reel_enrichment_service.md" in f for f in findings))

    def test_accepts_the_phrase_when_a_question_is_filed_for_that_cards_task(self) -> None:
        # Given the same card, with a question filed against the task that owns it
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "reel_enrichment_service.md").write_text(
                "## Contract\nOPEN FOR RATIFICATION — the window rule may be wrong.\n"
            )
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)

            # When validating
            findings = self._phrase_findings(schematic_dir)

            # Then the phrase is not flagged — the question is the state
            self.assertEqual(findings, [])

    def test_flags_the_phrase_again_once_its_question_is_answered(self) -> None:
        # Given a card whose ratification question has been asked AND answered
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "components" / "reel_enrichment_service.md").write_text(
                "## Contract\nOPEN FOR RATIFICATION — the window rule may be wrong.\n"
            )
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "b.1", _QUESTION_KEY_CHOICE)
            _run_answer(schematic_dir, _TASK_QUESTION_ID_FIRST, _ANSWER_KEY_CHOICE)

            # When validating
            findings = self._phrase_findings(schematic_dir)

            # Then the stale prose is a finding again — only an OPEN question silences it
            self.assertTrue(any("reel_enrichment_service.md" in f for f in findings))

    def test_flags_awaiting_ratification_in_the_task_ledger(self) -> None:
        # Given tasks.md carrying the phrase with no question filed
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            tasks_md.write_text(
                tasks_md.read_text().replace(
                    "Feature ACs: 1.A, 1.B",
                    "Feature ACs: 1.A, 1.B\nNote: awaiting ratification of the cap",
                )
            )

            # When validating
            findings = self._phrase_findings(schematic_dir)

            # Then the ledger is flagged
            self.assertTrue(any("tasks.md" in f for f in findings))

    def test_flags_needs_user_sign_off_in_the_objective_ledger(self) -> None:
        # Given objective.md carrying the phrase — no task owns it
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            objective_md = schematic_dir / "objective.md"
            objective_md.write_text(
                objective_md.read_text() + "\n## Decision Log\n- cap of 15 needs user sign-off\n"
            )

            # When validating
            findings = self._phrase_findings(schematic_dir)

            # Then the ledger is flagged
            self.assertTrue(any("objective.md" in f for f in findings))


# Fixtures


# Fixtures:

_REVIEW_SLOT = "review"
_LENS_ONE_FILENAME = "lens_one.md"
_LENS_TWO_FILENAME = "lens_two.md"
_LENS_ONE_BODY = "## Lens — One\nfirst lens body\n"
_LENS_TWO_BODY = "## Lens — Two\nsecond lens body\n"
_MISSING_LENS_SOURCE = "file:.schematic/absent_lens.md"


def _gen_project_root_with_manifest(tmp: str, manifest: dict) -> Path:
    """Write a project root carrying the canonical manifest plus two stand-in standards modules."""
    project_root = Path(tmp)
    schematic_config_dir = project_root / ".schematic"
    schematic_config_dir.mkdir(parents=True)
    (schematic_config_dir / _LENS_ONE_FILENAME).write_text(_LENS_ONE_BODY)
    (schematic_config_dir / _LENS_TWO_FILENAME).write_text(_LENS_TWO_BODY)
    (schematic_config_dir / "standards.json").write_text(json.dumps(manifest) + "\n")
    return project_root


def _gen_project_root_with_review_sources(tmp: str, review_source: object) -> Path:
    """Write a project root whose manifest maps only the review slot to review_source."""
    return _gen_project_root_with_manifest(tmp, manifest={_REVIEW_SLOT: review_source})


def _gen_lens_source(filename: str) -> str:
    """A manifest source string pointing at one of the stand-in modules."""
    return f"file:.schematic/{filename}"

# Fixtures


class TestMultiSourceReviewSlot(unittest.TestCase):

    def test_review_slot_string_source_still_resolves(self) -> None:
        # Given a manifest mapping review to a single string source
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=_gen_lens_source(_LENS_ONE_FILENAME),
            )

            # When resolving the slots
            slot_to_paths = _cli._resolved_slot_paths(project_root)

            # Then the review slot holds that one module
            self.assertEqual(
                slot_to_paths[_REVIEW_SLOT],
                [project_root / ".schematic" / _LENS_ONE_FILENAME],
            )

    def test_review_slot_list_of_sources_resolves_in_order(self) -> None:
        # Given a manifest mapping review to an ordered list of sources
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=[
                    _gen_lens_source(_LENS_ONE_FILENAME),
                    _gen_lens_source(_LENS_TWO_FILENAME),
                ],
            )

            # When resolving the slots
            slot_to_paths = _cli._resolved_slot_paths(project_root)

            # Then both modules resolve, in manifest order
            self.assertEqual(
                slot_to_paths[_REVIEW_SLOT],
                [
                    project_root / ".schematic" / _LENS_ONE_FILENAME,
                    project_root / ".schematic" / _LENS_TWO_FILENAME,
                ],
            )

    def test_string_source_that_does_not_exist_is_refused(self) -> None:
        # Given a slot mapped to a single module that is not on disk
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=_MISSING_LENS_SOURCE,
            )

            # Then resolution refuses the manifest, exactly as it does for a listed source
            with self.assertRaises(SystemExit):
                # When resolving the slots
                _cli._resolved_slot_paths(project_root)

    def test_review_slot_list_with_an_unresolvable_source_is_refused(self) -> None:
        # Given a list naming a module that is not on disk
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=[
                    _gen_lens_source(_LENS_ONE_FILENAME),
                    _MISSING_LENS_SOURCE,
                ],
            )

            # Then resolution refuses the manifest
            with self.assertRaises(SystemExit):
                # When resolving the slots
                _cli._resolved_slot_paths(project_root)

    def test_sweep_prompt_inlines_every_review_source_under_its_own_header(self) -> None:
        # Given a manifest with two review lenses
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=[
                    _gen_lens_source(_LENS_ONE_FILENAME),
                    _gen_lens_source(_LENS_TWO_FILENAME),
                ],
            )

            # When building the standards block for a python batch
            standards_content = _cli._resolve_standards_content_for_batch(
                batch_files=["src/a.py"],
                project_root=project_root,
            )

            # Then each lens is inlined under its own headed section, in order
            first_header = f"── review ({_gen_lens_source(_LENS_ONE_FILENAME)}) ──"
            second_header = f"── review ({_gen_lens_source(_LENS_TWO_FILENAME)}) ──"
            self.assertIn(first_header, standards_content)
            self.assertIn(second_header, standards_content)
            self.assertIn(_LENS_ONE_BODY.strip(), standards_content)
            self.assertIn(_LENS_TWO_BODY.strip(), standards_content)
            self.assertLess(
                standards_content.index(first_header),
                standards_content.index(second_header),
            )

    def test_sql_only_batch_inlines_the_sql_styling_module(self) -> None:
        # Given a manifest mapping sql styling, and a batch of only migration files
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_manifest(
                tmp,
                manifest={"styling": {"sql": _gen_lens_source(_LENS_ONE_FILENAME)}},
            )

            # When building the standards block
            standards_content = _cli._resolve_standards_content_for_batch(
                batch_files=["config/db/schema/migrations/trengine/019_drop.sql"],
                project_root=project_root,
            )

            # Then the sql module is inlined under its own header
            self.assertIn(
                f"── styling.sql ({_gen_lens_source(_LENS_ONE_FILENAME)}) ──",
                standards_content,
            )
            self.assertIn(_LENS_ONE_BODY.strip(), standards_content)

    def test_init_labels_the_canonical_repo_manifest_as_its_source(self) -> None:
        # Given a repo carrying the canonical .schematic/ manifest
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=_gen_lens_source(_LENS_ONE_FILENAME),
            )

            # When reporting manifest coverage
            report_output = _captured_stdout(
                _cli._report_standards_manifest,
                project_root=project_root,
            )

            # Then the label names the file actually loaded, not the .claude/ fallback
            self.assertIn("standards: .schematic/standards.json (repo manifest)", report_output)

    def test_correctness_model_is_read_from_the_manifest_and_defaults_to_inherit(self) -> None:
        # Given one manifest pinning a correctness model and one leaving it unset
        with TemporaryDirectory() as tmp:
            pinned_root = _gen_project_root_with_manifest(
                tmp,
                manifest={"schematic": {"reviewModel": "sonnet", "correctnessModel": "opus"}},
            )

            # When resolving the correctness model
            pinned_model = _cli._resolve_correctness_model(pinned_root)

            # Then the manifest value wins
            self.assertEqual(pinned_model, "opus")

        with TemporaryDirectory() as tmp:
            unset_root = _gen_project_root_with_manifest(
                tmp,
                manifest={"schematic": {"reviewModel": "sonnet"}},
            )

            # When resolving with no correctnessModel set
            inherited_model = _cli._resolve_correctness_model(unset_root)

            # Then it is None — inherit the session's planning model
            self.assertIsNone(inherited_model)

    def test_init_reports_every_review_source(self) -> None:
        # Given a manifest with two review lenses
        with TemporaryDirectory() as tmp:
            project_root = _gen_project_root_with_review_sources(
                tmp,
                review_source=[
                    _gen_lens_source(_LENS_ONE_FILENAME),
                    _gen_lens_source(_LENS_TWO_FILENAME),
                ],
            )

            # When reporting manifest coverage
            report_output = _captured_stdout(
                _cli._report_standards_manifest,
                project_root=project_root,
            )

            # Then both module paths are printed
            self.assertIn(str(project_root / ".schematic" / _LENS_ONE_FILENAME), report_output)
            self.assertIn(str(project_root / ".schematic" / _LENS_TWO_FILENAME), report_output)


class TestRosterPresent(unittest.TestCase):
    """schematic roster present — the only legitimate way to open the Phase 2 roster gate."""

    def test_invalid_draft_launches_nothing_and_writes_nothing(self) -> None:
        # Given a draft that fails mermaid validation
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            draft_path = Path(tmp) / "draft.mmd"
            draft_path.write_text("not a diagram\n")
            args = _make_args(num=2, schematic=schematic_dir.name, file=draft_path)

            # When present runs against an invalid draft
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
                 patch.object(_cli, "_validate_mermaid_file", return_value=["unrecognised diagram type"]), \
                 patch.object(_cli, "_launch_roster_editor") as mock_launch:
                with self.assertRaises(SystemExit) as exit_context:
                    _cli._roster_present(args)

            # Then it exits non-zero, launches nothing, writes no canonical, records no state
            self.assertEqual(exit_context.exception.code, 1)
            mock_launch.assert_not_called()
            self.assertFalse((schematic_dir / _cli.ROSTER_FILENAME).exists())
            self.assertNotIn("roster", _cli.load_state(schematic_dir)["phases"].get("2", {}))

    def test_valid_draft_writes_canonical_records_state_and_emits_stamped_envelope(self) -> None:
        # Given a draft that passes validation and a stubbed editor launch
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            draft_path = Path(tmp) / "draft.mmd"
            draft_body = "flowchart TD\n  A[Node]\n"
            draft_path.write_text(draft_body)
            args = _make_args(num=2, schematic=schematic_dir.name, file=draft_path)
            launched_editor = _cli.LaunchedEditor(pid=4242, url="http://127.0.0.1:5555/")

            # When present runs with a clean validation and a stubbed launch
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
                 patch.object(_cli, "find_project_root", return_value=Path(tmp)), \
                 patch.object(_cli, "_validate_mermaid_file", return_value=[]), \
                 patch.object(_cli, "_launch_roster_editor", return_value=launched_editor):
                envelope_output = _captured_stdout(_cli._roster_present, args=args)

            # Then canonical roster.mmd holds the draft body verbatim
            self.assertEqual((schematic_dir / _cli.ROSTER_FILENAME).read_text(), draft_body)

            # Then state records the presentation with a nonce and the editor identity
            roster_state = _cli.load_state(schematic_dir)["phases"]["2"]["roster"]
            self.assertEqual(roster_state["editor_url"], "http://127.0.0.1:5555/")
            self.assertEqual(roster_state["editor_pid"], 4242)
            self.assertTrue(roster_state["nonce"])

            # Then the stamped envelope carries that same nonce in both fences, plus url + sigil + watcher
            recorded_nonce = roster_state["nonce"]
            self.assertIn(f"⟦schematic·roster present=2 nonce={recorded_nonce}", envelope_output)
            self.assertIn(f"⟦/schematic·roster nonce={recorded_nonce}⟧", envelope_output)
            self.assertIn("http://127.0.0.1:5555/", envelope_output)
            self.assertIn("Confirm: y/comment", envelope_output)
            self.assertIn("watcher.py", envelope_output)


_ROSTER_OBJECTIVE_MD = textwrap.dedent("""\
    # Test Feature

    ## Functional ACs
    Part of change set: recover transcripts

    ### 1. Alpha recovers
    Class: AlphaResolver

    | AC | Title | What | Why |
    |---|---|---|---|
    | 1.A | do alpha | x | y |

    ### 2. Beta recovers
    Class: BetaClient

    | AC | Title | What | Why |
    |---|---|---|---|
    | 2.A | do beta | x | y |
    | 2.B | more beta | x | y |

    ## Key Findings
      - none
""")


class TestRosterInit(unittest.TestCase):
    """schematic roster init — Phase 2 entry launches a blank skeleton editor; nothing the agent authors precedes it."""

    def test_init_scaffolds_blank_skeleton_launches_and_records_state(self) -> None:
        # Given a fresh schematic whose objective carries two Phase-1 features
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "objective.md").write_text(_ROSTER_OBJECTIVE_MD)
            args = _make_args(num=2, schematic=schematic_dir.name)
            launched_editor = _cli.LaunchedEditor(pid=4242, url="http://127.0.0.1:5555/")

            # When init runs with a real validation and a stubbed launch
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
                 patch.object(_cli, "find_project_root", return_value=Path(tmp)), \
                 patch.object(_cli, "_launch_roster_editor", return_value=launched_editor):
                envelope_output = _captured_stdout(_cli._roster_init, args=args)

            # Then the scaffolded roster.mmd is a valid, blank, one-subgraph-per-feature skeleton
            skeleton_text = (schematic_dir / _cli.ROSTER_FILENAME).read_text()
            self.assertEqual(_cli._validate_mermaid_file(schematic_dir / _cli.ROSTER_FILENAME), [])
            self.assertIn('subgraph F1["F1 · Alpha recovers (1.A)"]', skeleton_text)
            self.assertIn('subgraph F2["F2 · Beta recovers (2.A 2.B)"]', skeleton_text)
            self.assertIn("F1 ~~~ F2", skeleton_text)
            self.assertIn("classDef new fill:#14532d,stroke:#4ade80,color:#fff", skeleton_text)
            self.assertIn(_cli.ROSTER_SKELETON_TODO_LABEL, skeleton_text)

            # Then the launch is recorded in state and the stamped envelope is emitted
            roster_state = _cli.load_state(schematic_dir)["phases"]["2"]["roster"]
            self.assertEqual(roster_state["editor_pid"], 4242)
            self.assertIn(f"⟦schematic·roster present=2 nonce={roster_state['nonce']}", envelope_output)

    def test_init_relaunches_existing_roster_without_clobbering_it(self) -> None:
        # Given a roster.mmd the agent has already filled
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "objective.md").write_text(_ROSTER_OBJECTIVE_MD)
            filled_roster = "flowchart TB\n  A[FilledNode]\n"
            (schematic_dir / _cli.ROSTER_FILENAME).write_text(filled_roster)
            args = _make_args(num=2, schematic=schematic_dir.name)
            launched_editor = _cli.LaunchedEditor(pid=1, url="http://127.0.0.1:5555/")

            # When init runs again
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
                 patch.object(_cli, "find_project_root", return_value=Path(tmp)), \
                 patch.object(_cli, "_launch_roster_editor", return_value=launched_editor):
                _cli._roster_init(args)

            # Then the filled canvas is preserved verbatim, never overwritten by the skeleton
            self.assertEqual((schematic_dir / _cli.ROSTER_FILENAME).read_text(), filled_roster)

    def test_init_exits_when_phase1_has_no_features(self) -> None:
        # Given an objective with no Phase-1 feature headings
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "objective.md").write_text("# Test\n\n## Functional ACs\nnothing here\n")
            args = _make_args(num=2, schematic=schematic_dir.name)

            # When init runs
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir), \
                 patch.object(_cli, "_launch_roster_editor") as mock_launch:
                with self.assertRaises(SystemExit) as exit_context:
                    _cli._roster_init(args)

            # Then it exits non-zero, launches nothing, writes no roster
            self.assertEqual(exit_context.exception.code, 1)
            mock_launch.assert_not_called()
            self.assertFalse((schematic_dir / _cli.ROSTER_FILENAME).exists())


class TestPhaseSignoffRosterGate(unittest.TestCase):
    """Phase 2 sign-off cannot lock unless the roster editor launch was recorded."""

    def test_phase2_signoff_blocked_when_roster_never_launched(self) -> None:
        # Given a Phase 2 with no recorded roster launch
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            args = _make_args(num=2, schematic=schematic_dir.name)

            # When sign-off is attempted
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir):
                with self.assertRaises(SystemExit) as exit_context:
                    _cli._phase_signoff(args)

            # Then it is refused and the phase stays unsigned
            self.assertEqual(exit_context.exception.code, 1)
            self.assertNotEqual(
                _cli.load_state(schematic_dir)["phases"].get("2", {}).get("signed_off"),
                True,
            )

    def test_phase2_signoff_succeeds_after_roster_recorded(self) -> None:
        # Given a Phase 2 whose roster launch is recorded
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["phases"].setdefault("2", {})["roster"] = {"nonce": "abc123"}
            _cli.save_state(schematic_dir, state)
            args = _make_args(num=2, schematic=schematic_dir.name)

            # When sign-off runs
            with patch.object(_cli, "resolve_schematic_dir", return_value=schematic_dir):
                _cli._phase_signoff(args)

            # Then the phase is signed off
            self.assertIs(_cli.load_state(schematic_dir)["phases"]["2"]["signed_off"], True)


# Fixtures


_MILESTONES_TABLE_HEADER = (
    "## Milestones\n"
    "\n"
    "| Milestone | Title | Scope | Proves |\n"
    "|---|---|---|---|"
)

_MILESTONE_ROWS_BY_GROUP = [
    "| M1 | Foundation ready | a | The foundation service exists. |",
    "| M2 | Enrichment ready | b | Enrichment runs end to end. |",
]


def _tasks_md_with_milestone_rows(rows: list[str]) -> str:
    """The fixture tasks.md with a `## Milestones` table above the detailed blocks."""
    table = "\n".join([_MILESTONES_TABLE_HEADER, *rows])
    return _TASKS_MD.replace("# Tasks\n", f"# Tasks\n\n{table}\n")


def _write_milestone_rows(schematic_dir: Path, rows: list[str]) -> None:
    (schematic_dir / "tasks.md").write_text(_tasks_md_with_milestone_rows(rows))


def _seed_milestone_state(
    schematic_dir: Path,
    decision: str,
    locked: bool,
    signed_off_ids: list[str],
) -> None:
    """Write the milestones gate state the way decide / lock / sign-off would leave it."""
    state = _cli.load_state(schematic_dir)
    state["milestones"] = {
        "decision": decision,
        "decided_at": "2026-09-26T00:00:00+00:00",
        "proposed_at": "2026-09-26T00:01:00+00:00" if locked else None,
        "locked_at": "2026-09-26T00:02:00+00:00" if locked else None,
        "signed_off": {
            milestone_id: "2026-09-26T00:03:00+00:00"
            for milestone_id in signed_off_ids
        },
        "reported": {},
        "announced": {},
        "suite": {},
        "amendments": [],
    }
    _cli.save_state(schematic_dir, state)


def _make_milestoned_schematic_dir(tmp: str) -> Path:
    """A bundle whose tasks.md carries a locked two-milestone table (M1 → group a, M2 → group b)."""
    schematic_dir = _make_schematic_dir(tmp)
    _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)
    _seed_milestone_state(
        schematic_dir,
        decision="yes",
        locked=True,
        signed_off_ids=[],
    )
    return schematic_dir


def _drop_milestone_table(schematic_dir: Path) -> None:
    """Rewrite tasks.md without its `## Milestones` table, leaving the locked state behind."""
    (schematic_dir / "tasks.md").write_text(_TASKS_MD)


def _record_clean_review(schematic_dir: Path, tag: str) -> None:
    state = _cli.load_state(schematic_dir)
    state["tasks"].setdefault(tag, {})["review_request"] = {
        "tag": tag,
        "status": "clean",
        "summary": f"{tag} reviewed clean",
    }
    _cli.save_state(schematic_dir, state)


def _mark_task_complete(schematic_dir: Path, tag: str) -> None:
    """Complete a task in tasks.md and the state file, with its clean review recorded."""
    _cli.update_task_status_in_file(schematic_dir / "tasks.md", tag, "complete")
    _record_clean_review(schematic_dir, tag)
    state = _cli.load_state(schematic_dir)
    state["tasks"].setdefault(tag, {})["status"] = "complete"
    _cli.save_state(schematic_dir, state)


def _record_pristine_sweep(schematic_dir: Path, milestone_id: str | None) -> None:
    state = _cli.load_state(schematic_dir)
    state["sweeps"].append({
        "sweep_id": len(state["sweeps"]) + 1,
        "batches": [],
        "pristine": True,
        "skipped_clean": [],
        "milestone": milestone_id,
    })
    _cli.save_state(schematic_dir, state)


def _seed_run_mode(schematic_dir: Path, mode: str) -> None:
    state = _cli.load_state(schematic_dir)
    state["run"] = {"mode": mode, "goal": "g", "base_ref": "BASE", "started_at": "t"}
    _cli.save_state(schematic_dir, state)


def _captured_handler_stdout(schematic_dir: Path, handler: Any, args: Any) -> str:
    """Run a --schematic handler against this bundle and return everything it printed."""
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        _with_resolved_dir(schematic_dir, handler, args)
    return captured.getvalue()


class TestParseMilestones(unittest.TestCase):

    def test_parses_every_row_of_the_milestones_table(self) -> None:
        # Given a tasks.md with a two-row Milestones table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When it is parsed
            milestones = _cli.parse_milestones(schematic_dir / "tasks.md")

            # Then both rows come back as whole records, in table order
            self.assertEqual(
                milestones,
                [
                    _cli.Milestone(
                        id="M1",
                        title="Foundation ready",
                        scope=("a",),
                        proves="The foundation service exists.",
                    ),
                    _cli.Milestone(
                        id="M2",
                        title="Enrichment ready",
                        scope=("b",),
                        proves="Enrichment runs end to end.",
                    ),
                ],
            )

    def test_parses_group_letters_and_explicit_tags_in_one_scope(self) -> None:
        # Given a scope cell mixing a group letter and an explicit tag
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(
                schematic_dir,
                ["| M1 | Mixed scope | a, b.1 | Both kinds of token. |"],
            )

            # When it is parsed
            milestones = _cli.parse_milestones(schematic_dir / "tasks.md")

            # Then both tokens are kept, in cell order
            self.assertEqual(milestones[0].scope, ("a", "b.1"))

    def test_returns_empty_list_when_no_milestones_section(self) -> None:
        # Given a tasks.md with no Milestones heading
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # When it is parsed
            milestones = _cli.parse_milestones(schematic_dir / "tasks.md")

            # Then nothing is declared
            self.assertEqual(milestones, [])

    def test_returns_empty_list_when_file_missing(self) -> None:
        # Given / When parsing a tasks.md that does not exist
        with TemporaryDirectory() as tmp:
            milestones = _cli.parse_milestones(Path(tmp) / "tasks.md")

            # Then nothing is declared
            self.assertEqual(milestones, [])

    def test_parses_a_row_whose_cells_carry_extra_whitespace(self) -> None:
        # Given a row padded with extra spaces in every cell
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(
                schematic_dir,
                ["|   M1   |   Padded title   |   a ,  b   |   Padded proves.   |"],
            )

            # When it is parsed
            milestones = _cli.parse_milestones(schematic_dir / "tasks.md")

            # Then every field is trimmed
            self.assertEqual(
                milestones[0],
                _cli.Milestone(
                    id="M1",
                    title="Padded title",
                    scope=("a", "b"),
                    proves="Padded proves.",
                ),
            )


# Fixtures


class TestMilestoneMembership(unittest.TestCase):

    def test_maps_every_task_to_its_milestone_by_group_letter(self) -> None:
        # Given milestones scoped to group a and group b
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"

            # When membership is resolved
            tag_to_milestone_id = _cli._tag_to_milestone_id(
                tasks=_cli.parse_tasks(tasks_md),
                milestones=_cli.parse_milestones(tasks_md),
            )

            # Then every task belongs to the milestone holding its group letter
            self.assertEqual(tag_to_milestone_id, {"a.1": "M1", "b.1": "M2", "b.2": "M2"})

    def test_explicit_tag_scope_wins_over_group_scope(self) -> None:
        # Given M1 scoped to group b and M2 naming b.2 explicitly
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(
                schematic_dir,
                [
                    "| M1 | Group scope | a, b | Everything by group. |",
                    "| M2 | Pulled out | b.2 | One task pulled forward. |",
                ],
            )
            tasks_md = schematic_dir / "tasks.md"

            # When membership is resolved
            tag_to_milestone_id = _cli._tag_to_milestone_id(
                tasks=_cli.parse_tasks(tasks_md),
                milestones=_cli.parse_milestones(tasks_md),
            )

            # Then the explicit tag owns b.2 and the group keeps the rest
            self.assertEqual(tag_to_milestone_id, {"a.1": "M1", "b.1": "M1", "b.2": "M2"})


# Fixtures


class TestMilestoneDecideGate(unittest.TestCase):

    def _lock_phase(self, schematic_dir: Path, num: int, override: str | None) -> None:
        args = _make_args(num=num, schematic=schematic_dir.name, override=override)
        launcher_url = "http://127.0.0.1:65000/"
        with patch.object(_cli, "_launch_dashboard", return_value=launcher_url) as launcher:
            self._launcher = launcher
            _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

    def _seed_gated_phase(self, schematic_dir: Path, num: int) -> None:
        state = _cli.load_state(schematic_dir)
        state["phases"][str(num)] = {"audit_result": "clean", "signed_off": True}
        _cli.save_state(schematic_dir, state)

    def test_phase_7_complete_fails_without_a_milestone_decision(self) -> None:
        # Given a phase 7 audited and signed off, with no milestone decision recorded
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_gated_phase(schematic_dir, 7)

            # When the phase is locked
            with self.assertRaises(SystemExit):
                self._lock_phase(schematic_dir, 7, override=None)

            # Then it stays unlocked
            self.assertNotEqual(
                _cli.load_state(schematic_dir)["phases"]["7"].get("status"),
                "locked",
            )

    def test_phase_7_complete_locks_after_deciding_no(self) -> None:
        # Given a decision to deliver as one stage
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_gated_phase(schematic_dir, 7)
            _seed_milestone_state(
                schematic_dir,
                decision="no",
                locked=False,
                signed_off_ids=[],
            )

            # When the phase is locked
            self._lock_phase(schematic_dir, 7, override=None)

            # Then it locks
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["7"]["status"], "locked")

    def test_phase_7_complete_locks_after_deciding_yes_and_locking_the_milestones(self) -> None:
        # Given a yes decision with the milestones locked
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._seed_gated_phase(schematic_dir, 7)

            # When the phase is locked
            self._lock_phase(schematic_dir, 7, override=None)

            # Then it locks
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["7"]["status"], "locked")

    def test_phase_7_complete_fails_when_yes_was_decided_but_the_milestones_are_unlocked(self) -> None:
        # Given a yes decision whose milestones were never locked
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_gated_phase(schematic_dir, 7)
            _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=False,
                signed_off_ids=[],
            )

            # When the phase is locked
            with self.assertRaises(SystemExit):
                self._lock_phase(schematic_dir, 7, override=None)

            # Then it stays unlocked
            self.assertNotEqual(
                _cli.load_state(schematic_dir)["phases"]["7"].get("status"),
                "locked",
            )

    def test_phase_7_complete_locks_with_override_despite_a_missing_decision(self) -> None:
        # Given a phase 7 with no milestone decision
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_gated_phase(schematic_dir, 7)

            # When it is locked with an override
            self._lock_phase(schematic_dir, 7, override="milestones deferred by the user")

            # Then it locks and the override is recorded
            locked_state = _cli.load_state(schematic_dir)
            self.assertEqual(locked_state["phases"]["7"]["status"], "locked")
            self.assertGreaterEqual(len(locked_state["overrides"]), 1)

    def test_phase_6_complete_does_not_require_a_milestone_decision(self) -> None:
        # Given a phase 6 audited and signed off, with no milestone decision
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            (schematic_dir / "sequence.mmd").write_text(_VALID_SEQUENCE_MMD)
            (schematic_dir / "components" / "_overview.md").write_text(
                "# Overview\n\n## Sequence Diagram\n\ncontent\n"
            )
            self._seed_gated_phase(schematic_dir, 6)

            # When the phase is locked
            self._lock_phase(schematic_dir, 6, override=None)

            # Then it locks
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["6"]["status"], "locked")

    def test_phase_8_complete_fails_while_a_milestone_is_unsigned(self) -> None:
        # Given a phase 8 signed off with its report on disk and M1/M2 unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            (schematic_dir / "implementation_report.md").write_text("# Report\n")
            state = _cli.load_state(schematic_dir)
            state["phases"]["8"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)

            # When the phase is locked
            with self.assertRaises(SystemExit):
                self._lock_phase(schematic_dir, 8, override=None)

            # Then it stays unlocked
            self.assertNotEqual(
                _cli.load_state(schematic_dir)["phases"]["8"].get("status"),
                "locked",
            )

    def test_phase_8_complete_locks_with_override_despite_an_unsigned_milestone(self) -> None:
        # Given the same phase 8 with an unsigned milestone
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            (schematic_dir / "implementation_report.md").write_text("# Report\n")
            state = _cli.load_state(schematic_dir)
            state["phases"]["8"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)

            # When it is locked with an override
            self._lock_phase(schematic_dir, 8, override="shipping M2 in the next cycle")

            # Then it locks and the override is recorded
            locked_state = _cli.load_state(schematic_dir)
            self.assertEqual(locked_state["phases"]["8"]["status"], "locked")
            self.assertGreaterEqual(len(locked_state["overrides"]), 1)

    def test_phase_8_complete_launches_the_whole_dashboard_on_lock(self) -> None:
        # Given a phase 8 whose every milestone is signed off
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            (schematic_dir / "implementation_report.md").write_text("# Report\n")
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=True,
                signed_off_ids=["M1", "M2"],
            )
            state = _cli.load_state(schematic_dir)
            state["phases"]["8"] = {"signed_off": True}
            _cli.save_state(schematic_dir, state)

            # When the phase is locked
            self._lock_phase(schematic_dir, 8, override=None)

            # Then the dashboard is opened on the whole bundle, not one milestone
            self._launcher.assert_called_once_with(schematic_dir=schematic_dir, fragment="")

    def _seed_lockable_phase_8(self, schematic_dir: Path) -> None:
        (schematic_dir / "implementation_report.md").write_text("# Report\n")
        _seed_milestone_state(
            schematic_dir,
            decision="yes",
            locked=True,
            signed_off_ids=["M1", "M2"],
        )
        state = _cli.load_state(schematic_dir)
        state["phases"]["8"] = {"signed_off": True}
        _cli.save_state(schematic_dir, state)

    def test_phase_8_complete_locks_and_warns_when_the_dashboard_never_starts(self) -> None:
        # Given a lockable phase 8 whose dashboard reports no URL
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._seed_lockable_phase_8(schematic_dir)
            args = _make_args(num=8, schematic=schematic_dir.name, override=None)

            # When the phase is locked
            captured = io.StringIO()
            with patch.object(_cli, "_launch_dashboard", return_value=None), \
                 contextlib.redirect_stdout(captured):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

            # Then the lock stands and the failure is a warning with the manual command
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["8"]["status"], "locked")
            self.assertIn("schematic overview", captured.getvalue())

    def test_phase_8_complete_skips_the_dashboard_when_no_browser_is_set(self) -> None:
        # Given an operator who asked for no browser
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._seed_lockable_phase_8(schematic_dir)
            args = _make_args(num=8, schematic=schematic_dir.name, override=None)

            # When the phase is locked
            with patch.dict("os.environ", {"SCHEMATIC_NO_BROWSER": "1"}), \
                 patch.object(_cli, "_launch_dashboard") as launcher, \
                 contextlib.redirect_stdout(io.StringIO()):
                _with_resolved_dir(schematic_dir, _cli._phase_complete, args)

            # Then nothing is spawned and the phase still locks
            launcher.assert_not_called()
            self.assertEqual(_cli.load_state(schematic_dir)["phases"]["8"]["status"], "locked")

    def test_decide_records_the_answer_and_its_timestamp(self) -> None:
        # Given a bundle with no milestone decision
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            args = _make_args(answer="yes", schematic=schematic_dir.name)

            # When the decision is recorded
            _captured_handler_stdout(schematic_dir, _cli._milestone_decide, args)

            # Then the answer and its timestamp are stored
            milestone_state = _cli.load_state(schematic_dir)["milestones"]
            self.assertEqual(milestone_state["decision"], "yes")
            self.assertTrue(milestone_state["decided_at"])

    def test_decide_refuses_after_the_milestones_are_locked(self) -> None:
        # Given locked milestones
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            args = _make_args(answer="no", schematic=schematic_dir.name)

            # When the decision is re-taken
            with self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._milestone_decide, args)

            # Then the recorded decision is untouched
            self.assertEqual(
                _cli.load_state(schematic_dir)["milestones"]["decision"],
                "yes",
            )


    def test_phase_8_complete_fails_when_the_locked_table_is_gone(self) -> None:
        # Given a lockable phase 8 whose Milestones table was deleted after lock
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._seed_lockable_phase_8(schematic_dir)
            _drop_milestone_table(schematic_dir)

            # When the phase is locked
            captured_error = io.StringIO()
            with contextlib.redirect_stderr(captured_error):
                with self.assertRaises(SystemExit):
                    self._lock_phase(schematic_dir, 8, override=None)

            # Then it refuses on the lost table and phase 8 stays unlocked
            self.assertIn("milestones locked in state but no `## Milestones` table in tasks.md", captured_error.getvalue())
            self.assertNotEqual(_cli.load_state(schematic_dir)["phases"]["8"].get("status"), "locked")


# Fixtures


class TestMilestonePropose(unittest.TestCase):

    def _propose(self, schematic_dir: Path) -> str:
        args = _make_args(schematic=schematic_dir.name)
        return _captured_handler_stdout(schematic_dir, _cli._milestone_propose, args)

    def _seed_proposable(self, schematic_dir: Path, rows: list[str]) -> None:
        _write_milestone_rows(schematic_dir, rows)
        _seed_milestone_state(
            schematic_dir,
            decision="yes",
            locked=False,
            signed_off_ids=[],
        )

    def test_propose_echoes_the_resolved_membership_for_every_milestone(self) -> None:
        # Given a valid two-milestone table awaiting the gate
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_proposable(schematic_dir, _MILESTONE_ROWS_BY_GROUP)

            # When it is proposed
            printed = self._propose(schematic_dir)

            # Then each milestone is printed with the tasks it claims
            self.assertIn("M1", printed)
            self.assertIn("a.1", printed)
            self.assertIn("M2", printed)
            self.assertIn("b.1", printed)
            self.assertIn("b.2", printed)

    def test_propose_accepts_a_dependency_on_an_earlier_milestone(self) -> None:
        # Given b.1 in M2 blocked by a.1 in M1
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_proposable(schematic_dir, _MILESTONE_ROWS_BY_GROUP)

            # When it is proposed
            printed = self._propose(schematic_dir)

            # Then the proposal stands and points at the lock
            self.assertIn("milestone lock", printed)

    def test_propose_refuses_when_the_decision_is_no(self) -> None:
        # Given a recorded decision to deliver as one stage
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)
            _seed_milestone_state(
                schematic_dir,
                decision="no",
                locked=False,
                signed_off_ids=[],
            )

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)

    def test_propose_refuses_when_no_decision_is_recorded(self) -> None:
        # Given a table but no recorded decision
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)

    def test_propose_refuses_when_the_table_is_missing(self) -> None:
        # Given a yes decision with no Milestones table written
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=False,
                signed_off_ids=[],
            )

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)

    def test_propose_refuses_a_task_in_no_milestone(self) -> None:
        # Given a table covering group a only
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_proposable(
                schematic_dir,
                ["| M1 | Foundation ready | a | Only the foundation. |"],
            )

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)

    def test_propose_refuses_a_task_in_two_milestones(self) -> None:
        # Given two milestones both claiming group b
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_proposable(
                schematic_dir,
                [
                    "| M1 | Foundation ready | a, b | Foundation and enrichment. |",
                    "| M2 | Enrichment ready | b | Enrichment again. |",
                ],
            )

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)

    def test_propose_refuses_a_dependency_on_a_later_milestone(self) -> None:
        # Given group b in M1 depending on group a in M2
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_proposable(
                schematic_dir,
                [
                    "| M1 | Enrichment first | b | Enrichment before its foundation. |",
                    "| M2 | Foundation later | a | The foundation afterwards. |",
                ],
            )

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)

    def test_propose_refuses_non_sequential_milestone_ids(self) -> None:
        # Given ids M1 and M3
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_proposable(
                schematic_dir,
                [
                    "| M1 | Foundation ready | a | The foundation. |",
                    "| M3 | Enrichment ready | b | Enrichment. |",
                ],
            )

            # When / Then proposing is refused
            with self.assertRaises(SystemExit):
                self._propose(schematic_dir)


# Fixtures


class TestMilestoneLock(unittest.TestCase):

    def _lock(self, schematic_dir: Path) -> str:
        args = _make_args(schematic=schematic_dir.name)
        return _captured_handler_stdout(schematic_dir, _cli._milestone_lock, args)

    def test_lock_records_the_lock_timestamp(self) -> None:
        # Given a valid proposed table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=False,
                signed_off_ids=[],
            )

            # When it is locked
            self._lock(schematic_dir)

            # Then the lock timestamp is recorded
            self.assertTrue(_cli.load_state(schematic_dir)["milestones"]["locked_at"])

    def test_lock_refuses_before_a_yes_decision(self) -> None:
        # Given a table with no yes decision
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)

            # When / Then locking is refused
            with self.assertRaises(SystemExit):
                self._lock(schematic_dir)

    def test_lock_refuses_when_membership_is_incomplete(self) -> None:
        # Given a table covering group a only
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(
                schematic_dir,
                ["| M1 | Foundation ready | a | Only the foundation. |"],
            )
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=False,
                signed_off_ids=[],
            )

            # When locking is attempted
            with self.assertRaises(SystemExit):
                self._lock(schematic_dir)

            # Then nothing is locked
            self.assertIsNone(_cli.load_state(schematic_dir)["milestones"]["locked_at"])

    def test_lock_refuses_when_already_locked(self) -> None:
        # Given locked milestones
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When / Then re-locking is refused
            with self.assertRaises(SystemExit):
                self._lock(schematic_dir)


class TestMilestoneBoundary(unittest.TestCase):

    def _run_task_next(self, schematic_dirs: list[Path], peek: bool) -> tuple[str, Any]:
        args = _make_args(name=None, peek=peek)
        captured = io.StringIO()
        launcher_url = "http://127.0.0.1:65000/"
        with patch.object(_cli, "_resolve_single_or_all", return_value=schematic_dirs), \
             patch.object(_cli, "_launch_milestone_dashboard", return_value=launcher_url) as launcher, \
             contextlib.redirect_stdout(captured):
            _cli._task_next(args)
        return captured.getvalue(), launcher

    def test_task_next_claims_a_task_from_the_open_milestone(self) -> None:
        # Given M1 (group a) still holding a pending task
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "a.1", "pending")

            # When the next task is requested
            self._run_task_next([schematic_dir], peek=False)

            # Then M1's task is claimed and M2's is untouched
            self.assertEqual(_status_of(schematic_dir, "a.1"), "in_progress")
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pending")

    def test_task_next_serves_nothing_from_a_later_milestone_until_sign_off(self) -> None:
        # Given M1 drained and unsigned, with M2's tasks pending
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the next task is requested
            self._run_task_next([schematic_dir], peek=False)

            # Then no M2 task is claimed
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pending")

    def test_task_next_serves_the_next_milestones_task_after_sign_off(self) -> None:
        # Given M1 signed off
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=True,
                signed_off_ids=["M1"],
            )

            # When the next task is requested
            self._run_task_next([schematic_dir], peek=False)

            # Then M2's first unblocked task is claimed
            self.assertEqual(_status_of(schematic_dir, "b.1"), "in_progress")

    def test_task_next_at_the_boundary_writes_the_report_and_opens_the_dashboard(self) -> None:
        # Given M1 drained and unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the next task is requested
            printed, launcher = self._run_task_next([schematic_dir], peek=False)

            # Then M1's section is written and the dashboard is opened on it
            report_text = (schematic_dir / "implementation_report.md").read_text()
            self.assertIn("## Milestone M1 — Foundation ready", report_text)
            self.assertIn("## Milestone M1", printed)
            launcher.assert_called_once_with(schematic_dir=schematic_dir, milestone_id="M1")

    def test_task_next_at_the_boundary_prints_the_sign_off_command(self) -> None:
        # Given M1 drained and unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the next task is requested
            printed, _ = self._run_task_next([schematic_dir], peek=False)

            # Then the one command that lifts the gate is printed
            self.assertIn("milestone sign-off M1", printed)

    def test_task_next_ignores_milestones_when_none_are_declared(self) -> None:
        # Given a bundle with no Milestones table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # When the next task is requested
            printed, launcher = self._run_task_next([schematic_dir], peek=False)

            # Then the first unblocked task is claimed and no boundary fires
            self.assertEqual(_status_of(schematic_dir, "b.1"), "in_progress")
            self.assertNotIn("Milestone", printed)
            launcher.assert_not_called()

    def test_task_next_peek_does_not_look_past_the_boundary(self) -> None:
        # Given M1 drained and unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the board is peeked
            printed, launcher = self._run_task_next([schematic_dir], peek=True)

            # Then no M2 task is shown or claimed, and nothing is written or launched
            self.assertNotIn("b.1", printed)
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pending")
            self.assertFalse((schematic_dir / "implementation_report.md").exists())
            launcher.assert_not_called()

    def test_task_next_does_not_fire_the_boundary_twice_for_one_milestone(self) -> None:
        # Given a boundary already announced once
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._run_task_next([schematic_dir], peek=False)

            # When the next task is requested again
            _, launcher = self._run_task_next([schematic_dir], peek=False)

            # Then the dashboard is not reopened and the section is not duplicated
            launcher.assert_not_called()
            report_text = (schematic_dir / "implementation_report.md").read_text()
            self.assertEqual(report_text.count("## Milestone M1"), 1)

    def test_task_next_still_announces_the_boundary_after_an_explicit_report(self) -> None:
        # Given M1 already reported on demand, mid-milestone, by the agent
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            report_args = _make_args(id="M1", schematic=schematic_dir.name, suite=None)
            with contextlib.redirect_stdout(io.StringIO()):
                _with_resolved_dir(schematic_dir, _cli._milestone_report, report_args)

            # When the board drains and the next task is requested
            printed, launcher = self._run_task_next([schematic_dir], peek=False)

            # Then the boundary is still announced and the dashboard still opens
            launcher.assert_called_once_with(schematic_dir=schematic_dir, milestone_id="M1")
            self.assertIn("MILESTONE M1 HIT", printed)

    def test_task_next_names_the_open_milestone_and_its_unfinished_tasks_when_gated(self) -> None:
        # Given M1's only task held on a question, so nothing is servable and nothing is drained
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "a.1", "pendingInput")

            # When the next task is requested
            printed, launcher = self._run_task_next([schematic_dir], peek=False)

            # Then the open milestone and what it is waiting on are named, and no boundary fires
            self.assertIn("M1", printed)
            self.assertIn("a.1", printed)
            self.assertIn("no pending unblocked tasks found", printed)
            launcher.assert_not_called()

    def test_task_next_skips_the_dashboard_at_the_boundary_when_no_browser_is_set(self) -> None:
        # Given an operator who asked for no browser
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the boundary is hit
            with patch.dict("os.environ", {"SCHEMATIC_NO_BROWSER": "1"}):
                printed, launcher = self._run_task_next([schematic_dir], peek=False)

            # Then the report still lands and only the launch is skipped
            launcher.assert_not_called()
            self.assertIn("## Milestone M1", (schematic_dir / "implementation_report.md").read_text())
            self.assertIn("SCHEMATIC_NO_BROWSER", printed)
            self.assertIn("milestone sign-off M1", printed)

    def test_task_next_serves_a_second_bundles_task_before_a_gated_bundles_boundary(self) -> None:
        # Given a gated bundle listed before a bundle with servable work
        with TemporaryDirectory() as tmp:
            gated_dir = _make_milestoned_schematic_dir(tmp)
            open_dir = _make_schematic_dir(tmp, "other-feature")

            # When the next task is requested across both
            _, launcher = self._run_task_next([gated_dir, open_dir], peek=False)

            # Then the servable task wins and no boundary is announced
            self.assertEqual(_status_of(open_dir, "b.1"), "in_progress")
            launcher.assert_not_called()


    def test_task_next_refuses_when_the_locked_table_is_gone(self) -> None:
        # Given locked milestones whose table was deleted from tasks.md
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _drop_milestone_table(schematic_dir)

            # When the next task is requested
            captured_error = io.StringIO()
            with contextlib.redirect_stderr(captured_error):
                with self.assertRaises(SystemExit):
                    self._run_task_next([schematic_dir], peek=False)

            # Then it refuses instead of serving past the lost gate
            self.assertIn("milestones locked in state but no `## Milestones` table in tasks.md", captured_error.getvalue())
            self.assertEqual(_status_of(schematic_dir, "b.1"), "pending")

    def test_task_next_announces_a_second_bundles_boundary_past_one_already_waiting(self) -> None:
        # Given one bundle already announced and waiting, and a second freshly drained
        with TemporaryDirectory() as tmp:
            waiting_dir = _make_milestoned_schematic_dir(tmp)
            self._run_task_next([waiting_dir], peek=False)
            fresh_dir = _make_schematic_dir(tmp, "other-feature")
            _write_milestone_rows(fresh_dir, _MILESTONE_ROWS_BY_GROUP)
            _seed_milestone_state(
                fresh_dir,
                decision="yes",
                locked=True,
                signed_off_ids=[],
            )

            # When the next task is requested across both
            printed, launcher = self._run_task_next([waiting_dir, fresh_dir], peek=False)

            # Then the waiting bundle is named and the fresh boundary still fires
            self.assertIn("still waiting on your sign-off", printed)
            self.assertIn("milestone sign-off M1 --schematic test-feature", printed)
            self.assertIn("MILESTONE M1 HIT", printed)
            launcher.assert_called_once_with(schematic_dir=fresh_dir, milestone_id="M1")

    def test_task_next_peek_names_a_drained_milestone_awaiting_sign_off(self) -> None:
        # Given M1 drained and unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the board is peeked
            printed, _ = self._run_task_next([schematic_dir], peek=True)

            # Then the drained boundary and its sign-off command are named
            self.assertIn("M1 is drained", printed)
            self.assertIn("milestone sign-off M1 --schematic test-feature", printed)

    def test_task_next_prints_the_dashboard_url_with_the_milestone_fragment(self) -> None:
        # Given M1 drained and unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When the boundary is hit
            printed, _ = self._run_task_next([schematic_dir], peek=False)

            # Then the printed URL deep-links to M1's report
            self.assertIn("dashboard: http://127.0.0.1:65000/#milestone:M1", printed)


# Fixtures


class TestMilestoneSignOff(unittest.TestCase):

    def _sign_off(self, schematic_dir: Path, milestone_id: str) -> str:
        args = _make_args(id=milestone_id, schematic=schematic_dir.name)
        return _captured_handler_stdout(schematic_dir, _cli._milestone_signoff, args)

    def _refused_sign_off(self, schematic_dir: Path, milestone_id: str) -> str:
        """Attempt a sign-off that must refuse; return everything it printed, stdout and stderr."""
        args = _make_args(id=milestone_id, schematic=schematic_dir.name)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            with self.assertRaises(SystemExit):
                _with_resolved_dir(schematic_dir, _cli._milestone_signoff, args)
        return captured.getvalue()

    def test_sign_off_records_the_milestone_when_every_gate_is_clean(self) -> None:
        # Given M1 complete with a clean per-task review
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _mark_task_complete(schematic_dir, "a.1")

            # When it is signed off
            self._sign_off(schematic_dir, "M1")

            # Then the sign-off is recorded
            self.assertIn("M1", _cli.load_state(schematic_dir)["milestones"]["signed_off"])

    def test_sign_off_refuses_while_a_task_is_incomplete(self) -> None:
        # Given M1's task back in pending
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "a.1", "pending")

            # When sign-off is attempted
            refusal = self._refused_sign_off(schematic_dir, "M1")

            # Then the completeness gate refuses and nothing is signed off
            self.assertIn("task a.1 is 'pending' — every task of a milestone must be complete", refusal)
            self.assertEqual(_cli.load_state(schematic_dir)["milestones"]["signed_off"], {})

    def test_sign_off_refuses_while_a_task_is_pending_input(self) -> None:
        # Given M1's task held on a question
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "a.1", "pendingInput")

            # When sign-off is attempted
            refusal = self._refused_sign_off(schematic_dir, "M1")

            # Then the held-task gate refuses
            self.assertIn("task a.1 is held on a user answer", refusal)

    def test_sign_off_refuses_when_a_task_has_no_clean_review_verdict(self) -> None:
        # Given M1 complete but never reviewed
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When sign-off is attempted
            refusal = self._refused_sign_off(schematic_dir, "M1")

            # Then the per-task review gate refuses, naming the tag
            self.assertIn("task a.1 holds no clean per-task review (verdict: never dispatched)", refusal)

    def test_sign_off_refuses_in_auto_mode_when_no_sweep_for_the_milestone_is_pristine(self) -> None:
        # Given an auto run with no sweep recorded for M1
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _mark_task_complete(schematic_dir, "a.1")
            _seed_run_mode(schematic_dir, "auto")

            # When sign-off is attempted
            refusal = self._refused_sign_off(schematic_dir, "M1")

            # Then the sweep gate refuses
            self.assertIn("no PRISTINE standards sweep recorded for M1", refusal)

    def test_sign_off_succeeds_in_auto_mode_when_the_milestones_sweep_is_pristine(self) -> None:
        # Given an auto run whose M1 sweep is PRISTINE
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _mark_task_complete(schematic_dir, "a.1")
            _seed_run_mode(schematic_dir, "auto")
            _record_pristine_sweep(schematic_dir, "M1")

            # When it is signed off
            self._sign_off(schematic_dir, "M1")

            # Then the sign-off is recorded
            self.assertIn("M1", _cli.load_state(schematic_dir)["milestones"]["signed_off"])

    def test_sign_off_does_not_require_a_sweep_in_manual_mode(self) -> None:
        # Given a manual run with no sweep at all
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _mark_task_complete(schematic_dir, "a.1")
            _seed_run_mode(schematic_dir, "manual")

            # When it is signed off
            printed = self._sign_off(schematic_dir, "M1")

            # Then it is recorded and the absent sweep is stated, not implied
            self.assertIn("M1", _cli.load_state(schematic_dir)["milestones"]["signed_off"])
            self.assertIn("no standards sweep", printed)

    def test_sign_off_refuses_when_an_earlier_milestone_is_unsigned(self) -> None:
        # Given every task complete but M1 unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            for tag in ["a.1", "b.1", "b.2"]:
                _mark_task_complete(schematic_dir, tag)

            # When M2 is signed off first
            refusal = self._refused_sign_off(schematic_dir, "M2")

            # Then the ordering gate refuses and nothing is signed off
            self.assertIn("sign the milestones off in order — M1 is still open", refusal)
            self.assertEqual(_cli.load_state(schematic_dir)["milestones"]["signed_off"], {})

    def test_sign_off_refuses_an_unknown_milestone_id(self) -> None:
        # Given a two-milestone table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When an id that does not exist is signed off
            refusal = self._refused_sign_off(schematic_dir, "M9")

            # Then the refusal names it and the ids that do exist
            self.assertIn("unknown milestone 'M9' — this bundle declares M1, M2", refusal)

    def test_sign_off_refuses_when_already_signed_off(self) -> None:
        # Given M1 already signed off
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _mark_task_complete(schematic_dir, "a.1")
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=True,
                signed_off_ids=["M1"],
            )

            # When it is signed off again
            refusal = self._refused_sign_off(schematic_dir, "M1")

            # Then the already-signed gate refuses
            self.assertIn("milestone M1 is already signed off (2026-09-26T00:03:00+00:00)", refusal)


class TestMilestoneReport(unittest.TestCase):

    def _report(self, schematic_dir: Path, milestone_id: str, suite: str | None) -> str:
        args = _make_args(id=milestone_id, schematic=schematic_dir.name, suite=suite)
        captured = io.StringIO()
        with patch.object(_cli, "_launch_milestone_dashboard") as launcher, \
             contextlib.redirect_stdout(captured):
            _with_resolved_dir(schematic_dir, _cli._milestone_report, args)
        self._launcher = launcher
        return captured.getvalue()

    def _report_text(self, schematic_dir: Path) -> str:
        return (schematic_dir / "implementation_report.md").read_text()

    def test_report_writes_a_section_naming_every_task_of_the_milestone(self) -> None:
        # Given a drained M1
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then its task is named and another milestone's is not
            report_text = self._report_text(schematic_dir)
            self.assertIn("a.1", report_text)
            self.assertIn("FoundationService", report_text)
            self.assertNotIn("b.1", report_text)

    def test_report_carries_each_tasks_divergence_flag(self) -> None:
        # Given a.1 completed with a recorded divergence
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            tasks_md = schematic_dir / "tasks.md"
            tasks_md.write_text(
                tasks_md.read_text().replace(
                    "Component file: ./components/foundation_service.md",
                    "Component file: ./components/foundation_service.md\nDivergence: bridged-not-patched",
                )
            )

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then the divergence rides on the task's row
            self.assertIn("bridged-not-patched", self._report_text(schematic_dir))

    def test_report_lists_the_autonomous_decisions_of_the_milestones_tasks_only(self) -> None:
        # Given a decision recorded on a task in each milestone
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["tasks"]["a.1"] = {"decisions": [{"text": "named it FoundationService", "kind": "naming", "ts": "t"}]}
            state["tasks"]["b.1"] = {"decisions": [{"text": "placed it under enrichment", "kind": "placement", "ts": "t"}]}
            _cli.save_state(schematic_dir, state)

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then only M1's decision is folded in
            report_text = self._report_text(schematic_dir)
            self.assertIn("named it FoundationService", report_text)
            self.assertNotIn("placed it under enrichment", report_text)

    def test_report_lists_each_tasks_review_verdict_and_summary(self) -> None:
        # Given a clean review recorded for a.1
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _record_clean_review(schematic_dir, "a.1")

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then the verdict and its summary are in the section
            report_text = self._report_text(schematic_dir)
            self.assertIn("clean", report_text)
            self.assertIn("a.1 reviewed clean", report_text)

    def test_report_records_the_sweep_result_for_the_milestone(self) -> None:
        # Given a PRISTINE sweep stamped M1
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _record_pristine_sweep(schematic_dir, "M1")

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then the sweep result is in the section
            self.assertIn("PRISTINE", self._report_text(schematic_dir))

    def test_report_lists_the_open_questions_of_the_milestones_tasks(self) -> None:
        # Given an open question on a task in each milestone
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _claim_task(schematic_dir, "a.1")
            _claim_task(schematic_dir, "b.1")
            _run_task_ask(schematic_dir, "a.1", "which cache key does the window use?")
            _run_task_ask(schematic_dir, "b.1", "does a degenerate row get a stamp?")

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then only M1's question is listed
            report_text = self._report_text(schematic_dir)
            self.assertIn("which cache key does the window use?", report_text)
            self.assertNotIn("does a degenerate row get a stamp?", report_text)

    def test_report_records_the_suite_last_lines_passed_on_the_command(self) -> None:
        # Given the suite's last line for this milestone
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When M1 is reported with it
            self._report(schematic_dir, "M1", suite="Ran 155 tests in 4.4s — OK")

            # Then it is rendered and recorded
            self.assertIn("Ran 155 tests in 4.4s — OK", self._report_text(schematic_dir))
            self.assertEqual(
                _cli.load_state(schematic_dir)["milestones"]["suite"]["M1"],
                "Ran 155 tests in 4.4s — OK",
            )

    def test_report_renders_not_recorded_for_an_absent_suite_line(self) -> None:
        # Given no suite output ever recorded
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then the section says so rather than omitting the fact
            self.assertIn("not recorded", self._report_text(schematic_dir))

    def test_report_replaces_its_own_section_on_a_second_run(self) -> None:
        # Given M1 already reported
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self._report(schematic_dir, "M1", suite="first run")

            # When it is reported again with new suite output
            self._report(schematic_dir, "M1", suite="second run")

            # Then there is one section, carrying the newer content
            report_text = self._report_text(schematic_dir)
            self.assertEqual(report_text.count("## Milestone M1"), 1)
            self.assertIn("second run", report_text)
            self.assertNotIn("first run", report_text)

    def test_report_preserves_the_rest_of_the_implementation_report(self) -> None:
        # Given a report already carrying the feature's own sections
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            (schematic_dir / "implementation_report.md").write_text(
                "# Implementation report\n\n## Commit status\n\nnot committed\n"
            )

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then the existing sections survive alongside it
            report_text = self._report_text(schematic_dir)
            self.assertIn("## Commit status", report_text)
            self.assertIn("not committed", report_text)
            self.assertIn("## Milestone M1", report_text)

    def test_report_creates_the_implementation_report_when_absent(self) -> None:
        # Given no implementation_report.md on disk
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            self.assertFalse((schematic_dir / "implementation_report.md").exists())

            # When M1 is reported
            self._report(schematic_dir, "M1", suite=None)

            # Then the file is created with the section
            self.assertIn("## Milestone M1", self._report_text(schematic_dir))

    def test_report_refuses_an_unknown_milestone_id(self) -> None:
        # Given a two-milestone table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When / Then reporting an id that does not exist is refused
            with self.assertRaises(SystemExit):
                self._report(schematic_dir, "M9", suite=None)

    def test_report_does_not_launch_the_dashboard(self) -> None:
        # Given a drained M1
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When M1 is reported on demand
            self._report(schematic_dir, "M1", suite=None)

            # Then no browser is opened — the agent presents what was printed
            self._launcher.assert_not_called()


    def test_report_rewrite_keeps_a_following_section_intact(self) -> None:
        # Given a report whose M1 section is followed by a final-report section
        with TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "implementation_report.md"
            report_path.write_text(
                "# Report\n\n## Milestone M1 — Foundation ready\n\nold body\n\n## Summary\n\nfinal prose\n"
            )

            # When M1's section is rewritten
            _cli._write_milestone_report_section(
                report_path=report_path,
                heading="## Milestone M1 — Foundation ready",
                section_text="## Milestone M1 — Foundation ready\n\nnew body",
            )

            # Then only M1's body changes and the following section survives verbatim
            self.assertEqual(
                report_path.read_text(),
                "# Report\n\n## Milestone M1 — Foundation ready\n\nnew body\n\n## Summary\n\nfinal prose\n",
            )


# Fixtures


class TestMilestoneAmend(unittest.TestCase):

    def _amend(
        self,
        schematic_dir: Path,
        move: str | None,
        to: str | None,
        add: str | None,
        title: str | None,
        scope: str | None,
        proves: str | None,
    ) -> str:
        args = _make_args(
            schematic=schematic_dir.name,
            reason="mid-build re-scope",
            move=move,
            to=to,
            add=add,
            title=title,
            scope=scope,
            proves=proves,
        )
        return _captured_handler_stdout(schematic_dir, _cli._milestone_amend, args)

    def _scope_of(self, schematic_dir: Path, milestone_id: str) -> tuple[str, ...]:
        return next(
            milestone.scope
            for milestone in _cli.parse_milestones(schematic_dir / "tasks.md")
            if milestone.id == milestone_id
        )

    def test_amend_moves_a_tag_to_another_milestone_in_tasks_md(self) -> None:
        # Given b.1 owned by M2's group letter
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When it is moved to M1
            self._amend(
                schematic_dir, move="b.1", to="M1",
                add=None, title=None, scope=None, proves=None,
            )

            # Then tasks.md hands b.1 to M1
            tasks_md = schematic_dir / "tasks.md"
            tag_to_milestone_id = _cli._tag_to_milestone_id(
                tasks=_cli.parse_tasks(tasks_md),
                milestones=_cli.parse_milestones(tasks_md),
            )
            self.assertEqual(tag_to_milestone_id, {"a.1": "M1", "b.1": "M1", "b.2": "M2"})

    def test_amend_expands_a_group_scope_into_its_remaining_tags_when_a_tag_leaves(self) -> None:
        # Given M2 scoped to the whole of group b
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When b.1 leaves it
            self._amend(
                schematic_dir, move="b.1", to="M1",
                add=None, title=None, scope=None, proves=None,
            )

            # Then the group letter is expanded to what is left
            self.assertEqual(self._scope_of(schematic_dir, "M2"), ("b.2",))

    def test_amend_adds_a_new_milestone_row_at_the_end_of_the_table(self) -> None:
        # Given a two-milestone table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When a third milestone is added over b.2
            self._amend(
                schematic_dir, move=None, to=None,
                add="M3", title="Live probe", scope="b.2", proves="The probe returns text.",
            )

            # Then the table carries it last, as written
            milestones = _cli.parse_milestones(schematic_dir / "tasks.md")
            self.assertEqual(
                milestones[-1],
                _cli.Milestone(
                    id="M3",
                    title="Live probe",
                    scope=("b.2",),
                    proves="The probe returns text.",
                ),
            )

    def test_amend_records_the_delta_and_reason_in_state(self) -> None:
        # Given a locked table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When b.1 is moved
            self._amend(
                schematic_dir, move="b.1", to="M1",
                add=None, title=None, scope=None, proves=None,
            )

            # Then one amendment is recorded with its delta and reason
            amendments = _cli.load_state(schematic_dir)["milestones"]["amendments"]
            self.assertEqual(len(amendments), 1)
            self.assertIn("b.1", amendments[0]["delta"])
            self.assertEqual(amendments[0]["reason"], "mid-build re-scope")

    def test_amend_refuses_before_the_milestones_are_locked(self) -> None:
        # Given a proposed but unlocked table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(schematic_dir, _MILESTONE_ROWS_BY_GROUP)
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=False,
                signed_off_ids=[],
            )

            # When / Then amending is refused
            with self.assertRaises(SystemExit):
                self._amend(
                    schematic_dir, move="b.2", to="M1",
                    add=None, title=None, scope=None, proves=None,
                )

    def test_amend_refuses_a_move_that_leaves_a_task_in_no_milestone(self) -> None:
        # Given a destination id no milestone carries
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            tasks_before = (schematic_dir / "tasks.md").read_text()

            # When b.2 is moved into it
            with self.assertRaises(SystemExit):
                self._amend(
                    schematic_dir, move="b.2", to="M5",
                    add=None, title=None, scope=None, proves=None,
                )

            # Then tasks.md is untouched
            self.assertEqual((schematic_dir / "tasks.md").read_text(), tasks_before)

    def test_amend_refuses_a_destination_that_is_not_in_the_table(self) -> None:
        # Given a destination id no row declares
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When a tag is moved into it
            captured_error = io.StringIO()
            with contextlib.redirect_stderr(captured_error):
                with self.assertRaises(SystemExit):
                    self._amend(
                        schematic_dir, move="b.1", to="M5",
                        add=None, title=None, scope=None, proves=None,
                    )

            # Then the refusal names the unknown destination and the ids that exist
            self.assertIn("M5", captured_error.getvalue())
            self.assertIn("M1", captured_error.getvalue())

    def test_amend_refuses_a_move_into_a_signed_off_milestone(self) -> None:
        # Given M1 already signed off
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=True,
                signed_off_ids=["M1"],
            )

            # When / Then moving work into it is refused
            with self.assertRaises(SystemExit):
                self._amend(
                    schematic_dir, move="b.2", to="M1",
                    add=None, title=None, scope=None, proves=None,
                )

    def test_amend_refuses_without_either_a_move_or_an_add(self) -> None:
        # Given no delta named
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When / Then the amendment is refused
            with self.assertRaises(SystemExit):
                self._amend(
                    schematic_dir, move=None, to=None,
                    add=None, title=None, scope=None, proves=None,
                )

    def test_amend_refuses_an_add_missing_its_title_scope_or_proves(self) -> None:
        # Given an add with no title
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When / Then the amendment is refused
            with self.assertRaises(SystemExit):
                self._amend(
                    schematic_dir, move=None, to=None,
                    add="M3", title=None, scope="b.2", proves="The probe returns text.",
                )


    def test_amend_rearms_the_boundary_of_a_milestone_whose_scope_changed(self) -> None:
        # Given M1 announced, then b.1 moved into it and completed
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            state = _cli.load_state(schematic_dir)
            state["milestones"]["announced"]["M1"] = "2026-09-26T00:04:00+00:00"
            _cli.save_state(schematic_dir, state)
            self._amend(
                schematic_dir, move="b.1", to="M1",
                add=None, title=None, scope=None, proves=None,
            )
            _cli.update_task_status_in_file(schematic_dir / "tasks.md", "b.1", "complete")

            # When the next task is requested
            captured = io.StringIO()
            with patch.object(_cli, "_resolve_single_or_all", return_value=[schematic_dir]), \
                 patch.object(_cli, "_launch_milestone_dashboard", return_value="http://127.0.0.1:65000/") as launcher, \
                 contextlib.redirect_stdout(captured):
                _cli._task_next(_make_args(name=None, peek=False))

            # Then the re-drained M1 is reported and presented again
            self.assertIn("MILESTONE M1 HIT", captured.getvalue())
            launcher.assert_called_once_with(schematic_dir=schematic_dir, milestone_id="M1")


# Fixtures


class TestMilestoneValidate(unittest.TestCase):

    def _findings(self, schematic_dir: Path) -> list[str]:
        return _cli._validate_schematic(schematic_dir)

    def _seed_locked_rows(self, schematic_dir: Path, rows: list[str]) -> None:
        _write_milestone_rows(schematic_dir, rows)
        _seed_milestone_state(
            schematic_dir,
            decision="yes",
            locked=True,
            signed_off_ids=[],
        )

    def test_validate_flags_a_task_in_no_milestone(self) -> None:
        # Given a locked table covering group a only
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_locked_rows(
                schematic_dir,
                ["| M1 | Foundation ready | a | Only the foundation. |"],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the orphaned task is flagged
            self.assertTrue(any("no milestone claims this task" in f for f in findings))

    def test_validate_flags_a_task_in_two_milestones(self) -> None:
        # Given two milestones claiming group b
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_locked_rows(
                schematic_dir,
                [
                    "| M1 | Foundation ready | a, b | Foundation and enrichment. |",
                    "| M2 | Enrichment ready | b | Enrichment again. |",
                ],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the double claim is flagged
            self.assertTrue(any("claimed by more than one milestone" in f for f in findings))

    def test_validate_flags_a_dependency_on_a_later_milestone(self) -> None:
        # Given group b scheduled before the group a it depends on
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_locked_rows(
                schematic_dir,
                [
                    "| M1 | Enrichment first | b | Enrichment before its foundation. |",
                    "| M2 | Foundation later | a | The foundation afterwards. |",
                ],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the backwards dependency is flagged
            self.assertTrue(any("lands in the later milestone" in f for f in findings))

    def test_validate_flags_a_scope_token_that_is_neither_a_group_nor_a_tag(self) -> None:
        # Given a scope cell carrying a token of neither shape
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_locked_rows(
                schematic_dir,
                [
                    "| M1 | Foundation ready | a, Group-B | Foundation and enrichment. |",
                    "| M2 | Enrichment ready | b | Enrichment. |",
                ],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the token is flagged
            self.assertTrue(
                any("is neither a group letter nor a task tag" in f for f in findings)
            )

    def test_validate_flags_a_scope_group_matching_no_task(self) -> None:
        # Given a milestone scoped to a group with no tasks
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_locked_rows(
                schematic_dir,
                [
                    "| M1 | Foundation ready | a | The foundation. |",
                    "| M2 | Enrichment ready | b | Enrichment. |",
                    "| M3 | Nothing here | z | A group that does not exist. |",
                ],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the empty group is flagged
            self.assertTrue(any("matches no task" in f for f in findings))

    def test_validate_flags_non_sequential_milestone_ids(self) -> None:
        # Given a locked table whose ids skip from M1 to M3
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            self._seed_locked_rows(
                schematic_dir,
                [
                    "| M1 | Foundation ready | a | The foundation. |",
                    "| M3 | Enrichment ready | b | Enrichment. |",
                ],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the broken sequence is flagged with the ids it expected and found
            self.assertIn(
                "tasks.md — milestone ids must run M1, M2 in table order (found M1, M3)",
                findings,
            )

    def test_validate_is_clean_when_no_milestones_are_declared(self) -> None:
        # Given a bundle with no Milestones table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then no milestone rule fires at all
            self.assertEqual([f for f in findings if "milestone" in f.lower()], [])


    def test_validate_flags_a_locked_decision_whose_table_is_gone(self) -> None:
        # Given milestones locked in state, then the table deleted from tasks.md
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)
            _drop_milestone_table(schematic_dir)

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then the lost table is flagged
            self.assertIn("milestones locked in state but no `## Milestones` table in tasks.md", findings)

    def test_validate_ignores_a_broken_table_that_is_not_locked(self) -> None:
        # Given a table leaving group b unclaimed, decided yes but never locked
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)
            _write_milestone_rows(
                schematic_dir,
                ["| M1 | Foundation ready | a | Only the foundation. |"],
            )
            _seed_milestone_state(
                schematic_dir,
                decision="yes",
                locked=False,
                signed_off_ids=[],
            )

            # When the bundle is validated
            findings = self._findings(schematic_dir)

            # Then no milestone rule fires before lock
            self.assertEqual([f for f in findings if "milestone" in f.lower()], [])


# Fixtures


class TestMilestoneStatus(unittest.TestCase):

    def _status(self, schematic_dir: Path) -> str:
        args = _make_args(schematic=schematic_dir.name)
        return _captured_handler_stdout(schematic_dir, _cli._milestone_status, args)

    def test_status_prints_each_milestone_with_its_task_counts_and_gate_state(self) -> None:
        # Given a locked two-milestone table with M1 drained
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When status is printed
            printed = self._status(schematic_dir)

            # Then both milestones appear with their titles and task counts
            self.assertIn("Foundation ready", printed)
            self.assertIn("Enrichment ready", printed)
            self.assertIn("complete 1", printed)
            self.assertIn("pending 2", printed)

    def test_status_names_the_open_milestone(self) -> None:
        # Given M1 unsigned
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_milestoned_schematic_dir(tmp)

            # When status is printed
            printed = self._status(schematic_dir)

            # Then the open marker sits on M1's line
            m1_line = next(line for line in printed.splitlines() if "M1" in line)
            self.assertIn("open", m1_line)

    def test_status_reports_no_milestones_when_none_are_declared(self) -> None:
        # Given a bundle with no Milestones table
        with TemporaryDirectory() as tmp:
            schematic_dir = _make_schematic_dir(tmp)

            # When status is printed
            printed = self._status(schematic_dir)

            # Then it says so
            self.assertIn("no milestones declared", printed)


# Fixtures


class TestUiUrlPolling(unittest.TestCase):

    def _ui_process(self, exit_code: int | None) -> MagicMock:
        """A launched UI that has exited with this code, or is still running when None."""
        ui_process = MagicMock()
        ui_process.poll.return_value = exit_code
        ui_process.returncode = exit_code
        return ui_process

    def _refused_await(self, log_path: Path, ui_process: MagicMock) -> tuple[int, str]:
        captured_error = io.StringIO()
        with contextlib.redirect_stderr(captured_error):
            with self.assertRaises(SystemExit) as refusal:
                _cli._await_editor_url(
                    editor_log_path=log_path,
                    editor_process=ui_process,
                    url_prefix="Mermaid editor: ",
                )
        return refusal.exception.code, captured_error.getvalue()

    def test_polled_ui_url_is_none_when_the_ui_exits_first(self) -> None:
        # Given a UI that exited before logging a URL
        with TemporaryDirectory() as tmp:
            # When its URL is polled
            reported_url = _cli._polled_ui_url(
                editor_log_path=Path(tmp) / "ui.log",
                editor_process=self._ui_process(exit_code=1),
                url_prefix="Mermaid editor: ",
            )

            # Then there is no URL
            self.assertIsNone(reported_url)

    def test_polled_ui_url_is_none_when_the_ui_stays_silent_past_the_timeout(self) -> None:
        # Given a running UI that never logs a URL, and no time left to wait
        with TemporaryDirectory() as tmp, \
             patch.object(_cli, "EDITOR_LAUNCH_TIMEOUT_SECONDS", 0.0):
            # When its URL is polled
            reported_url = _cli._polled_ui_url(
                editor_log_path=Path(tmp) / "ui.log",
                editor_process=self._ui_process(exit_code=None),
                url_prefix="Mermaid editor: ",
            )

            # Then there is no URL
            self.assertIsNone(reported_url)

    def test_await_editor_url_exits_when_the_editor_exits_first(self) -> None:
        # Given an editor that exited before logging a URL
        with TemporaryDirectory() as tmp:
            # When its URL is awaited
            exit_code, error_text = self._refused_await(
                log_path=Path(tmp) / "ui.log",
                ui_process=self._ui_process(exit_code=1),
            )

            # Then it fails closed with the editor-exited wording
            self.assertEqual(exit_code, 1)
            self.assertIn("editor exited before opening (code 1)", error_text)

    def test_await_editor_url_exits_when_the_editor_stays_silent(self) -> None:
        # Given a running editor that never logs a URL, and no time left to wait
        with TemporaryDirectory() as tmp, \
             patch.object(_cli, "EDITOR_LAUNCH_TIMEOUT_SECONDS", 0.0):
            # When its URL is awaited
            exit_code, error_text = self._refused_await(
                log_path=Path(tmp) / "ui.log",
                ui_process=self._ui_process(exit_code=None),
            )

            # Then it fails closed with the editor-silent wording
            self.assertEqual(exit_code, 1)
            self.assertIn("editor did not report a URL", error_text)


# Fixtures


if __name__ == "__main__":
    unittest.main(verbosity=2)
