"""Shared agent responder — builds prompts for the session agent to answer questions from the UI.

Runtime-agnostic: does NOT shell out to any CLI (claude, kiro, etc). Each UI question is
compiled into a fully-contextualised prompt (diagram + bundle tree + Feature ACs + thread)
and queued in `<stem>.agent-requests.json` for the main session agent. The agent drains the
queue with `schematic questions` and replies with `schematic answer <id> "<text>"`, which
writes to `<stem>.answers.json` — the UI bubble polls that file and renders the reply live.
The answers file is NEVER written here: a raw prompt must never surface in the user's bubble.
"""
import json
import threading
from pathlib import Path

ENCODING = "utf-8"
ANSWERS_SUFFIX = ".answers.json"
AGENT_REQUESTS_SUFFIX = ".agent-requests.json"


def _build_bundle_context(bundle_dir: Path, companion_path: Path | None) -> str:
    """Build a file-tree + summary context for the schematic bundle."""
    lines = ["Schematic bundle files:"]
    for item in sorted(bundle_dir.rglob("*")):
        if item.is_file() and not item.name.startswith(".") and "__pycache__" not in str(item):
            rel = item.relative_to(bundle_dir)
            size_kb = item.stat().st_size / 1024
            lines.append(f"  {rel} ({size_kb:.1f}kb)")

    objective = bundle_dir / "objective.md"
    if objective.exists() and (not companion_path or companion_path.resolve() != objective.resolve()):
        content = objective.read_text(encoding=ENCODING)
        acs_section = ""
        for line in content.split("\n"):
            if line.startswith("## Functional ACs"):
                acs_section = "## Functional ACs\n"
            elif acs_section and line.startswith("## "):
                break
            elif acs_section:
                acs_section += line + "\n"
        if acs_section:
            lines.append(f"\nFeature ACs (from objective.md):\n{acs_section.strip()}")

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_prompt(
    question_text: str,
    context: str,
    diagram_path: Path | None = None,
    history: list[dict[str, str]] | None = None,
    companion_path: Path | None = None,
) -> str:
    """Build the full prompt text without dispatching to any CLI."""
    conversation = _format_history(history)
    companion_content = ""
    if companion_path and companion_path.exists():
        companion_content = companion_path.read_text(encoding=ENCODING)
    bundle_context = ""
    if diagram_path and diagram_path.exists():
        bundle_dir = diagram_path.parent
        bundle_context = _build_bundle_context(bundle_dir, companion_path)
        diagram_content = diagram_path.read_text(encoding=ENCODING)
        prompt = (
            f"You are helping a user edit a Mermaid diagram that is part of a software design schematic. "
            f"The current diagram content is:\n```mermaid\n{diagram_content}\n```\n\n"
        )
        if bundle_context:
            prompt += f"{bundle_context}\n\n"
        if companion_content and companion_path:
            prompt += f"Design context (from {companion_path.name}):\n{companion_content}\n\n"
        prompt += (
            f"Context: {context}\n"
            f"{conversation or f'User request: {question_text}'}\n\n"
            f"Respond to the user's latest message using the design context to ground your answer. "
            f"If they ask you to change the diagram, output ONLY the full updated mermaid content "
            f"between ```mermaid and ``` markers — no explanation, no partial snippets. "
            f"If it's a general question, answer concisely in 1-3 sentences referencing specific "
            f"classes, ACs, or components from the design context. "
            f"When referencing detail you don't have inline, point to the file path."
        )
    else:
        prompt = (
            f"You are a helpful assistant for a software schematic planning tool. "
            f"Context: {context}\n"
            f"{conversation or f'User question: {question_text}'}\n\n"
            f"Answer the user's latest message concisely in 1-3 sentences."
        )
    return prompt


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
    prompt = _build_prompt(
        question_text=question_text,
        context=context,
        diagram_path=diagram_path,
        history=history,
        companion_path=companion_path,
    )
    if diagram_path:
        prompt += (
            f"\n\nIf you edit the diagram, write the updated mermaid content to: {diagram_path} "
            f"(the editor hot-reloads it), then answer with what changed."
        )

    requests_path = _agent_requests_path(answers_path)
    _append_agent_request(
        requests_path=requests_path,
        server_idx=server_idx,
        question_text=question_text,
        prompt=prompt,
        file_lock=file_lock,
    )
    question_id = f"{requests_path.name[: -len(AGENT_REQUESTS_SUFFIX)]}#{server_idx}"
    print(
        f"Question {question_id} queued for the session agent: {question_text[:60]}\n"
        f"  answer with: schematic answer {question_id} \"<text>\"",
        flush=True,
    )


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


def _agent_requests_path(answers_path: Path) -> Path:
    """`sequence.answers.json` → `sequence.agent-requests.json` (same stem, sibling file)."""
    stem = answers_path.name[: -len(ANSWERS_SUFFIX)] if answers_path.name.endswith(ANSWERS_SUFFIX) else answers_path.stem
    return answers_path.parent / f"{stem}{AGENT_REQUESTS_SUFFIX}"


def _append_agent_request(
    requests_path: Path,
    server_idx: int,
    question_text: str,
    prompt: str,
    file_lock: threading.Lock | None = None,
) -> None:
    def _do_write() -> None:
        existing = json.loads(requests_path.read_text(encoding=ENCODING)) if requests_path.exists() else []
        existing = [r for r in existing if r.get("idx") != server_idx]
        existing.append({"idx": server_idx, "question": question_text, "prompt": prompt})
        requests_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)

    if file_lock:
        with file_lock:
            _do_write()
    else:
        _do_write()
