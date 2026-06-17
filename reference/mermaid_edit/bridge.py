import hashlib
import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_utils import open_in_ide, set_project_root
from agent_responder import spawn_answer

EDITOR_HTML = Path(__file__).parent / "editor.html"
MERMAID_JS = Path(__file__).parent / "mermaid.min.js"
QA_BUBBLE_JS = Path(__file__).parent / "qa-bubble-component.js"
CONTENT_PATH = "/content"
SAVE_PATH = "/save"
NOTE_PATH = "/note"
NOTES_LIST_PATH = "/notes"
NOTE_UPDATE_PATH = "/note-update"
NOTE_DELETE_PATH = "/note-delete"
QUESTION_PATH = "/question"
ANSWERS_PATH = "/answers"
OPEN_PATH = "/open"
PATHS_PATH = "/paths"
COMPANION_PATH = "/companion"
COMPANION_PATH_ENDPOINT = "/companion-path"
ENCODING = "utf-8"


def _discover_companion(diagram_path: Path) -> Path | None:
    """Find a markdown companion file for the diagram.

    Search order:
    1. Schematic bundle: use components/_overview.md (has edge inventory, summary table)
    2. Same name with .md extension (e.g. pipeline.md next to pipeline.mmd)
    3. README.md in the same directory
    4. Any single .md file in the same directory
    """
    parent = diagram_path.parent

    overview = parent / "components" / "_overview.md"
    if overview.exists():
        return overview

    same_name_md = parent / (diagram_path.stem + ".md")
    if same_name_md.exists():
        return same_name_md

    readme = parent / "README.md"
    if readme.exists():
        return readme

    md_files = list(parent.glob("*.md"))
    if len(md_files) == 1:
        return md_files[0]

    return None

_file_lock = threading.Lock()


class MermaidBridgeHandler(BaseHTTPRequestHandler):
    diagram_path: Path
    notes_path: Path
    questions_path: Path
    answers_path: Path
    paths_path: Path
    companion_path: Path | None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == CONTENT_PATH:
            self._respond(
                content=self.diagram_path.read_text(encoding=ENCODING),
                content_type="text/plain",
            )
            return
        if self.path == "/mermaid.min.js":
            self._respond(
                content=MERMAID_JS.read_text(encoding=ENCODING),
                content_type="application/javascript",
            )
            return
        if self.path == "/qa-bubble-component.js":
            self._respond(
                content=QA_BUBBLE_JS.read_text(encoding=ENCODING),
                content_type="application/javascript",
            )
            return
        if self.path == ANSWERS_PATH:
            answers = json.loads(self.answers_path.read_text(encoding=ENCODING)) if self.answers_path.exists() else []
            self._respond(
                content=json.dumps(answers),
                content_type="application/json",
            )
            return
        if self.path == PATHS_PATH:
            paths = json.loads(self.paths_path.read_text(encoding=ENCODING)) if self.paths_path.exists() else {}
            self._respond(
                content=json.dumps(paths),
                content_type="application/json",
            )
            return
        if self.path == NOTES_LIST_PATH:
            notes = json.loads(self.notes_path.read_text(encoding=ENCODING)) if self.notes_path.exists() else []
            self._respond(
                content=json.dumps(notes),
                content_type="application/json",
            )
            return
        if self.path == "/content-hash":
            content = self.diagram_path.read_text(encoding=ENCODING)
            content_hash = hashlib.sha256(content.encode(ENCODING)).hexdigest()
            self._respond(
                content=json.dumps({"hash": content_hash}),
                content_type="application/json",
            )
            return
        if self.path == COMPANION_PATH:
            if self.companion_path and self.companion_path.exists():
                self._respond(
                    content=self.companion_path.read_text(encoding=ENCODING),
                    content_type="text/plain",
                )
            else:
                self._respond(
                    content="",
                    content_type="text/plain",
                )
            return
        if self.path == COMPANION_PATH_ENDPOINT:
            path_str = str(self.companion_path) if self.companion_path else ""
            self._respond(
                content=json.dumps({"path": path_str}),
                content_type="application/json",
            )
            return
        self._respond(
            content=EDITOR_HTML.read_text(encoding=ENCODING),
            content_type="text/html",
        )

    def do_POST(self) -> None:
        content_length = self.headers.get("Content-Length")
        if not content_length or not content_length.isdigit():
            self.send_response(400)
            self.end_headers()
            return
        body_length = int(content_length)
        raw_body = self.rfile.read(body_length).decode(ENCODING)

        if self.path == NOTE_PATH:
            note = json.loads(raw_body)
            with _file_lock:
                existing = json.loads(self.notes_path.read_text(encoding=ENCODING)) if self.notes_path.exists() else []
                existing.append(note)
                self.notes_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond(content="ok", content_type="text/plain")
            return

        if self.path == NOTE_UPDATE_PATH:
            payload = json.loads(raw_body)
            idx = payload["idx"]
            new_text = payload["text"]
            with _file_lock:
                existing = json.loads(self.notes_path.read_text(encoding=ENCODING)) if self.notes_path.exists() else []
                if 0 <= idx < len(existing):
                    existing[idx]["text"] = new_text
                    self.notes_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond(content="ok", content_type="text/plain")
            return

        if self.path == NOTE_DELETE_PATH:
            payload = json.loads(raw_body)
            idx = payload["idx"]
            with _file_lock:
                existing = json.loads(self.notes_path.read_text(encoding=ENCODING)) if self.notes_path.exists() else []
                existing = [n for i, n in enumerate(existing) if i != idx]
                self.notes_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond(content="ok", content_type="text/plain")
            return

        if self.path == QUESTION_PATH:
            question = json.loads(raw_body)
            with _file_lock:
                existing = json.loads(self.questions_path.read_text(encoding=ENCODING)) if self.questions_path.exists() else []
                server_idx = len(existing)
                question["server_idx"] = server_idx
                existing.append(question)
                self.questions_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond(content=json.dumps({"idx": server_idx}), content_type="application/json")
            return

        if self.path == "/self-answer":
            answer = json.loads(raw_body)
            with _file_lock:
                existing = json.loads(self.answers_path.read_text(encoding=ENCODING)) if self.answers_path.exists() else []
                existing.append(answer)
                self.answers_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond(content="ok", content_type="text/plain")
            return

        if self.path == "/update-diagram":
            payload = json.loads(raw_body)
            content = payload.get("content")
            if content is None:
                self.send_response(400)
                self.end_headers()
                return
            self.diagram_path.write_text(content, encoding=ENCODING)
            self._respond(content=json.dumps({"ok": True}), content_type="application/json")
            return

        if self.path == OPEN_PATH:
            req = json.loads(raw_body)
            result = open_in_ide(ide=req.get("ide", "code"), file_path=req.get("path", ""))
            self._respond(content=result, content_type="text/plain")
            return

        if self.path == SAVE_PATH:
            self.diagram_path.write_text(raw_body, encoding=ENCODING)
            self._respond(content="ok", content_type="text/plain")
            return

        self.send_response(404)
        self.end_headers()

    def _respond(self, content: str, content_type: str) -> None:
        body = content.encode(ENCODING)
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset={ENCODING}")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def launch_editor(diagram_path: Path) -> None:
    # Set project root from the diagram's location so IDE paths resolve correctly
    search = diagram_path.resolve().parent
    while search != search.parent:
        if (search / ".git").exists():
            set_project_root(search)
            break
        search = search.parent

    MermaidBridgeHandler.diagram_path = diagram_path
    MermaidBridgeHandler.notes_path = diagram_path.with_suffix(".notes.json")
    MermaidBridgeHandler.questions_path = diagram_path.with_suffix(".questions.json")
    MermaidBridgeHandler.answers_path = diagram_path.with_suffix(".answers.json")
    MermaidBridgeHandler.paths_path = diagram_path.with_suffix(".paths.json")
    MermaidBridgeHandler.companion_path = _discover_companion(diagram_path)

    server = ThreadingHTTPServer(("127.0.0.1", 0), MermaidBridgeHandler)
    port = server.server_address[1]
    editor_url = f"http://127.0.0.1:{port}/"

    print(f"Mermaid editor: {editor_url}", flush=True)
    print(f"Questions file: {MermaidBridgeHandler.questions_path}", flush=True)
    print(f"Answers file: {MermaidBridgeHandler.answers_path}", flush=True)

    open_browser = "--no-browser" not in sys.argv
    if open_browser:
        webbrowser.open(editor_url)

    # Serve in background thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Watch for questions and answer them using claude CLI
    seen_count = 0
    questions_path = MermaidBridgeHandler.questions_path
    answers_path = MermaidBridgeHandler.answers_path

    try:
        while True:
            try:
                if questions_path.exists():
                    questions = json.loads(questions_path.read_text(encoding=ENCODING))
                    if len(questions) > seen_count:
                        for i in range(seen_count, len(questions)):
                            q = questions[i]
                            user_msgs = [m["text"] for m in q.get("thread", []) if m.get("role") == "user"]
                            if not user_msgs:
                                text = q.get("text", "")
                                if not text:
                                    continue
                            else:
                                text = user_msgs[-1]
                            server_idx = q.get("server_idx", q.get("idx", i))
                            answered = False
                            if answers_path.exists():
                                answers = json.loads(answers_path.read_text(encoding=ENCODING))
                                answered = any(a.get("idx") == server_idx for a in answers)
                            if not answered:
                                context = q.get("context", "diagram-edit")
                                spawn_answer(
                                    question_text=text,
                                    server_idx=server_idx,
                                    context=context,
                                    answers_path=answers_path,
                                    diagram_path=diagram_path,
                                    file_lock=_file_lock,
                                    history=q.get("thread"),
                                    companion_path=MermaidBridgeHandler.companion_path,
                                )
                        seen_count = len(questions)
            except (json.JSONDecodeError, KeyError):
                pass
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        print(f"\nSaved: {diagram_path}", flush=True)


if __name__ == "__main__":
    launch_editor(diagram_path=Path(sys.argv[1]))
