"""Shared agent responder — spawns claude CLI to answer questions from the UI."""
import json
import re
import subprocess
import threading
from pathlib import Path

ENCODING = "utf-8"


def answer_question(
    question_text: str,
    server_idx: int,
    context: str,
    answers_path: Path,
    diagram_path: Path | None = None,
    file_lock: threading.Lock | None = None,
    history: list[dict[str, str]] | None = None,
    companion_path: Path | None = None,
) -> None:
    conversation = _format_history(history)
    companion_content = ""
    if companion_path and companion_path.exists():
        companion_content = companion_path.read_text(encoding=ENCODING)
    if diagram_path and diagram_path.exists():
        diagram_content = diagram_path.read_text(encoding=ENCODING)
        prompt = (
            f"You are helping a user edit a Mermaid diagram that is part of a software design schematic. "
            f"The current diagram content is:\n```mermaid\n{diagram_content}\n```\n\n"
        )
        if companion_content:
            prompt += f"Design context (from companion doc):\n{companion_content}\n\n"
        prompt += (
            f"Context: {context}\n"
            f"{conversation or f'User request: {question_text}'}\n\n"
            f"Respond to the user's latest message using the design context to ground your answer. "
            f"If they ask you to change the diagram, output ONLY the full updated mermaid content "
            f"between ```mermaid and ``` markers — no explanation, no partial snippets. "
            f"If it's a general question, answer concisely in 1-3 sentences referencing specific "
            f"classes, ACs, or components from the design context."
        )
    else:
        prompt = (
            f"You are a helpful assistant for a software schematic planning tool. "
            f"Context: {context}\n"
            f"{conversation or f'User question: {question_text}'}\n\n"
            f"Answer the user's latest message concisely in 1-3 sentences."
        )

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )
        answer_text = result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"

        if diagram_path and diagram_path.exists():
            mermaid_match = re.search(r'```mermaid\n(.*?)```', answer_text, re.DOTALL)
            if mermaid_match:
                new_content = mermaid_match.group(1).strip()
                diagram_path.write_text(new_content + "\n", encoding=ENCODING)
                answer_text = "Done — diagram updated."

        _write_answer(answers_path, server_idx, answer_text, file_lock)
        print(f"Answered q#{server_idx}: {question_text[:60]}", flush=True)

    except subprocess.TimeoutExpired:
        _write_answer(answers_path, server_idx, "Timed out (120s). Try a simpler request.", file_lock)
    except FileNotFoundError:
        _write_answer(answers_path, server_idx, "claude CLI not found. Install: npm i -g @anthropic-ai/claude-code", file_lock)
    except Exception as e:
        _write_answer(answers_path, server_idx, f"Error: {e}", file_lock)


def _format_history(history: list[dict[str, str]] | None) -> str:
    """Render the Q&A thread as a labelled transcript so the agent sees prior turns."""
    if not history:
        return ""
    role_to_speaker = {"user": "User", "agent": "Assistant"}
    lines = [
        f"{role_to_speaker[m['role']]}: {m.get('text', '')}"
        for m in history
        if m.get("role") in role_to_speaker and m.get("text")
    ]
    if not lines:
        return ""
    return "Conversation so far:\n" + "\n".join(lines)


def spawn_answer(
    question_text: str,
    server_idx: int,
    context: str,
    answers_path: Path,
    diagram_path: Path | None = None,
    file_lock: threading.Lock | None = None,
    history: list[dict[str, str]] | None = None,
    companion_path: Path | None = None,
) -> None:
    threading.Thread(
        target=answer_question,
        args=(question_text, server_idx, context, answers_path, diagram_path, file_lock, history, companion_path),
        daemon=True,
    ).start()


def _write_answer(
    answers_path: Path,
    server_idx: int,
    answer_text: str,
    file_lock: threading.Lock | None = None,
) -> None:
    def _do_write() -> None:
        existing = json.loads(answers_path.read_text(encoding=ENCODING)) if answers_path.exists() else []
        existing.append({"idx": server_idx, "answer": answer_text})
        answers_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)

    if file_lock:
        with file_lock:
            _do_write()
    else:
        _do_write()
