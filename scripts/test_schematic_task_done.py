"""Tests for the schematic-task-done CLI.

Runs the CLI as a subprocess against temp tasks.md fixtures and verifies
the post-conditions: status line updated, divergence line appended (or not)
per the matched/updated matrix, exit codes correct on error paths.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


_CLI_PATH = Path(__file__).parent / "schematic-task-done"


# Fixtures:

_TASKS_FIXTURE_TWO_TASKS = """# Tasks

## b.1 | Create | UserRepository
Status: pending

Feature ACs: 1.A
Class AC: persists user
Component file: ./components/user_repository.md

## b.6 | Create | OnboardingService
Status: pending

Feature ACs: 2.A, 2.B
Class AC: orchestrates onboarding flow
Component file: ./components/onboarding_service.md

Test hierarchy:
  AC Tests (primary):
    - test_complete_writes_atomically
"""

_TASKS_FIXTURE_ALREADY_COMPLETE = """# Tasks

## c.3 | Tighten | InputsResolver
Status: complete

Feature ACs: 3.A
"""

_TASKS_FIXTURE_WITH_OLD_DIVERGENCE = """# Tasks

## d.1 | Create | FooService
Status: in_progress

Feature ACs: 4.A
Divergence: bridged-not-patched
"""

_TASKS_FIXTURE_NO_STATUS = """# Tasks

## e.1 | Create | BrokenTask
Feature ACs: 5.A
"""

_TASKS_FIXTURE_IN_REVIEW = """# Tasks

## f.2 | Create | ReviewedService
Status: review

Feature ACs: 6.A
Class AC: passes standards review before completion
"""


def _write_tasks_file(tmp_path: Path, content: str) -> Path:
    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text(content)
    return tasks_file


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_CLI_PATH), *args],
        capture_output=True,
        text=True,
    )


# Fixtures


class TestSchematicTaskDoneMarksCompleteOnMatched:

    def test_marks_complete_without_divergence_when_matched_y_updated_y(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.6",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert "## b.6 | Create | OnboardingService\nStatus: complete" in updated_content
        assert "Divergence:" not in updated_content

    def test_marks_complete_without_divergence_when_matched_y_updated_n(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.1",
                "--matched", "y",
                "--updated", "n",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert "## b.1 | Create | UserRepository\nStatus: complete" in updated_content
        assert "Divergence:" not in updated_content


class TestSchematicTaskDoneAppendsDivergenceOnNotMatched:

    def test_appends_patched_divergence_when_matched_n_updated_y(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.6",
                "--matched", "n",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert "Status: complete" in updated_content
        assert "Divergence: patched-in-component-file" in updated_content

    def test_appends_bridged_divergence_when_matched_n_updated_n(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.6",
                "--matched", "n",
                "--updated", "n",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert "Status: complete" in updated_content
        assert "Divergence: bridged-not-patched" in updated_content


class TestSchematicTaskDoneCompletesReviewStatusTask:

    def test_marks_complete_when_task_in_review_status(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_IN_REVIEW,
        )

        # When
        result = _run_cli(
            args=[
                "f.2",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert "## f.2 | Create | ReviewedService\nStatus: complete" in updated_content


class TestSchematicTaskDonePreservesFormatting:

    def test_preserves_blank_line_between_status_and_other_fields(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        _run_cli(
            args=[
                "b.6",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        updated_content = tasks_file.read_text()
        assert "Status: complete\n\nFeature ACs: 2.A, 2.B" in updated_content


class TestSchematicTaskDoneScopesEditToOneTask:

    def test_does_not_modify_other_task_blocks_when_marking_one_complete(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        _run_cli(
            args=[
                "b.6",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        updated_content = tasks_file.read_text()
        assert "## b.1 | Create | UserRepository\nStatus: pending" in updated_content


class TestSchematicTaskDoneReplacesPriorDivergenceLine:

    def test_replaces_old_divergence_line_when_remarking_with_different_status(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_WITH_OLD_DIVERGENCE,
        )

        # When
        result = _run_cli(
            args=[
                "d.1",
                "--matched", "n",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert updated_content.count("Divergence:") == 1
        assert "Divergence: patched-in-component-file" in updated_content
        assert "Divergence: bridged-not-patched" not in updated_content


class TestSchematicTaskDoneErrorPaths:

    def test_exits_nonzero_when_tag_not_found(self, tmp_path: Path) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "nonexistent.99",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 3
        assert "not found" in result.stderr

    def test_exits_nonzero_when_task_already_complete_without_force(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_ALREADY_COMPLETE,
        )

        # When
        result = _run_cli(
            args=[
                "c.3",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 4
        assert "already complete" in result.stderr

    def test_succeeds_when_remarking_already_complete_task_with_force(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_ALREADY_COMPLETE,
        )

        # When
        result = _run_cli(
            args=[
                "c.3",
                "--matched", "n",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
                "--force",
            ],
        )

        # Then
        assert result.returncode == 0
        updated_content = tasks_file.read_text()
        assert "Divergence: patched-in-component-file" in updated_content

    def test_exits_nonzero_when_task_block_has_no_status_line(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_NO_STATUS,
        )

        # When
        result = _run_cli(
            args=[
                "e.1",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 5
        assert "Status:" in result.stderr

    def test_exits_nonzero_when_tasks_file_does_not_exist(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        missing_file = tmp_path / "missing-tasks.md"

        # When
        result = _run_cli(
            args=[
                "b.1",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(missing_file),
            ],
        )

        # Then
        assert result.returncode == 2
        assert "not found" in result.stderr

    def test_exits_nonzero_when_required_flags_missing(self, tmp_path: Path) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.6",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode != 0


class TestSchematicTaskDoneStdout:

    def test_prints_completion_summary_with_divergence_when_diverged(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.6",
                "--matched", "n",
                "--updated", "n",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        assert "✓ Task b.6 marked complete" in result.stdout
        assert "bridged-not-patched" in result.stdout

    def test_prints_completion_summary_without_divergence_when_matched(
        self,
        tmp_path: Path,
    ) -> None:
        # Given
        tasks_file = _write_tasks_file(
            tmp_path=tmp_path,
            content=_TASKS_FIXTURE_TWO_TASKS,
        )

        # When
        result = _run_cli(
            args=[
                "b.6",
                "--matched", "y",
                "--updated", "y",
                "--tasks-file", str(tasks_file),
            ],
        )

        # Then
        assert result.returncode == 0
        assert "✓ Task b.6 marked complete" in result.stdout
        assert "Divergence" not in result.stdout
