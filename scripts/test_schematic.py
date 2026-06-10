#!/usr/bin/env python3

import argparse
import importlib.util
import json
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

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
            self.assertEqual(loaded_state, {"phases": {}, "tasks": {}, "overrides": []})

    def test_save_then_load_produces_identical_state(self) -> None:
        with TemporaryDirectory() as tmp:
            original_state = {
                "phases": {"1": {"status": "locked", "signed_off": True}},
                "tasks": {"a.1": {"status": "complete"}},
                "overrides": [],
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


# Fixtures


if __name__ == "__main__":
    unittest.main(verbosity=2)
