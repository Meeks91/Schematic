"""Editor wake-up watcher — exits the moment an unanswered question OR a new sticky note lands.

Run BACKGROUNDED alongside bridge.py. Background tasks notify the agent on
process EXIT, not on output — so this script exits (rather than looping
forever) the first time the queue holds an unanswered question or a note lands
that was not present when the watcher armed. The exit IS the wake-up call. On wake:
1. Drain the queue:   schematic questions   (and read new notes from <diagram>.notes.json)
2. Reply:             schematic answer <id> "<text>"
3. Re-arm:            relaunch this script (same command, backgrounded)

Usage: python3 watcher.py <mmd_file> [poll_seconds]
"""
import json
import sys
import time
from pathlib import Path

_DEFAULT_POLL_SECONDS = 2.0


def _load_entries(path: Path) -> list:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []


def _pending_count(questions: list, answers: list) -> int:
    answered_ids = {answer.get("idx") for answer in answers}
    pending = 0
    for position, question in enumerate(questions):
        question_id = question.get("server_idx", position)
        if question_id not in answered_ids:
            pending += 1
    return pending


def watch_until_pending(mmd_path: Path, poll_seconds: float) -> None:
    questions_path = mmd_path.with_suffix(".questions.json")
    answers_path = mmd_path.with_suffix(".answers.json")
    notes_path = mmd_path.with_suffix(".notes.json")
    note_count_at_arm = len(_load_entries(notes_path))
    while True:
        pending = _pending_count(
            questions=_load_entries(questions_path),
            answers=_load_entries(answers_path),
        )
        new_note_count = len(_load_entries(notes_path)) - note_count_at_arm
        if pending or new_note_count > 0:
            print(
                f"NEW EDITOR ACTIVITY: {pending} pending question(s),"
                f" {new_note_count} new note(s) — drain with 'schematic questions',"
                f" reply with 'schematic answer <id> ...', read new notes from"
                f" '<diagram>.notes.json', then re-arm this watcher.",
                flush=True,
            )
            return
        time.sleep(poll_seconds)


if __name__ == "__main__":
    watch_until_pending(
        mmd_path=Path(sys.argv[1]),
        poll_seconds=float(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_POLL_SECONDS,
    )
