"""Editor Q&A wake-up watcher — exits the moment an unanswered question lands.

Run BACKGROUNDED alongside bridge.py. Background tasks notify the agent on
process EXIT, not on output — so this script exits (rather than looping
forever) the first time the queue holds an unanswered question. The exit IS
the wake-up call. On wake:
1. Drain the queue:   schematic questions
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
    while True:
        pending = _pending_count(
            questions=_load_entries(questions_path),
            answers=_load_entries(answers_path),
        )
        if pending:
            print(
                f"NEW EDITOR QUESTION(S): {pending} pending — drain with"
                f" 'schematic questions', reply with 'schematic answer <id> ...',"
                f" then re-arm this watcher.",
                flush=True,
            )
            return
        time.sleep(poll_seconds)


if __name__ == "__main__":
    watch_until_pending(
        mmd_path=Path(sys.argv[1]),
        poll_seconds=float(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_POLL_SECONDS,
    )
