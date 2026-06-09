"""Watch for questions in the mermaid editor and answer them.

Called by Claude after launching bridge.py. This script:
1. Polls questions.json for new entries
2. Prints new questions to stdout (Claude reads and answers)
3. Claude posts answers via /self-answer

Usage from Claude session:
  python3 watcher.py <mmd_file> --port <port>
  # Prints new questions as JSON lines to stdout
  # Claude reads stdout, generates answer, calls /self-answer
"""
import json
import sys
import time
from pathlib import Path


def watch(mmd_path: Path, poll_interval: float = 1.0) -> None:
    questions_path = mmd_path.with_suffix(".questions.json")
    answers_path = mmd_path.with_suffix(".answers.json")
    seen_count = 0

    if questions_path.exists():
        seen_count = len(json.loads(questions_path.read_text()))

    print(json.dumps({"status": "watching", "questions_file": str(questions_path)}), flush=True)

    while True:
        try:
            if questions_path.exists():
                questions = json.loads(questions_path.read_text())
                if len(questions) > seen_count:
                    for i in range(seen_count, len(questions)):
                        q = questions[i]
                        user_messages = [m["text"] for m in q.get("thread", []) if m.get("role") == "user"]
                        latest_question = user_messages[-1] if user_messages else ""
                        answered = False
                        if answers_path.exists():
                            answers = json.loads(answers_path.read_text())
                            answered = any(a.get("idx") == q.get("server_idx") for a in answers)
                        if not answered and latest_question:
                            print(json.dumps({
                                "type": "question",
                                "server_idx": q["server_idx"],
                                "text": latest_question,
                                "x": q.get("x"),
                                "y": q.get("y"),
                            }), flush=True)
                    seen_count = len(questions)
        except (json.JSONDecodeError, KeyError):
            pass
        time.sleep(poll_interval)


if __name__ == "__main__":
    watch(mmd_path=Path(sys.argv[1]))
