"""schematic overview — Multi-tab schematic browser.

Lazy-loaded: only imported when `schematic overview` is invoked.
Launches a local HTTP server serving a single-page app for navigating
the full schematic (objective, components, diagrams, tasks, trace).
"""

import json
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "reference"))
from shared_utils import open_in_ide, set_project_root
from agent_responder import spawn_answer

ENCODING = "utf-8"
OVERVIEW_HTML = Path(__file__).parent.parent / "reference" / "overview_ui" / "overview.html"
MERMAID_COMPONENT_JS = Path(__file__).parent.parent / "reference" / "overview_ui" / "mermaid-editor-component.js"
MERMAID_MIN_JS = Path(__file__).parent.parent / "reference" / "mermaid_edit" / "mermaid.min.js"
MARKED_MIN_JS = Path(__file__).parent.parent / "reference" / "overview_ui" / "marked.min.js"
PURIFY_MIN_JS = Path(__file__).parent.parent / "reference" / "overview_ui" / "purify.min.js"
QA_BUBBLE_JS = Path(__file__).parent.parent / "reference" / "mermaid_edit" / "qa-bubble-component.js"


class OverviewHandler(BaseHTTPRequestHandler):
    schematic_dir: Path

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self._respond(OVERVIEW_HTML.read_text(encoding=ENCODING), "text/html")
            return

        if parsed.path == "/api/manifest":
            manifest = self._build_manifest()
            self._respond(json.dumps(manifest), "application/json")
            return

        if parsed.path == "/api/component/mermaid-editor":
            self._respond(MERMAID_COMPONENT_JS.read_text(encoding=ENCODING), "application/javascript")
            return

        if parsed.path == "/mermaid.min.js":
            self._respond(MERMAID_MIN_JS.read_text(encoding=ENCODING), "application/javascript")
            return

        if parsed.path == "/marked.min.js":
            self._respond(MARKED_MIN_JS.read_text(encoding=ENCODING), "application/javascript")
            return

        if parsed.path == "/purify.min.js":
            self._respond(PURIFY_MIN_JS.read_text(encoding=ENCODING), "application/javascript")
            return

        if parsed.path == "/qa-bubble-component.js":
            self._respond(QA_BUBBLE_JS.read_text(encoding=ENCODING), "application/javascript")
            return

        if parsed.path == "/api/file":
            params = parse_qs(parsed.query)
            file_name = params.get("name", [""])[0]
            file_path = (self.schematic_dir / file_name).resolve()
            if not file_path.is_relative_to(self.schematic_dir.resolve()):
                self._respond_error(403, "access denied")
                return
            if file_path.exists() and file_path.is_file():
                self._respond(file_path.read_text(encoding=ENCODING), "text/plain")
            else:
                self._respond_error(404, f"not found: {file_name}")
            return

        if parsed.path == "/api/answers":
            answers_path = self.schematic_dir / "overview.answers.json"
            try:
                answers = json.loads(answers_path.read_text(encoding=ENCODING)) if answers_path.exists() else []
            except json.JSONDecodeError:
                answers = []
            self._respond(json.dumps(answers), "application/json")
            return

        if parsed.path == "/api/state":
            state_path = self.schematic_dir / ".schematic-state.json"
            try:
                state = json.loads(state_path.read_text(encoding=ENCODING)) if state_path.exists() else {}
            except json.JSONDecodeError:
                state = {}
            self._respond(json.dumps(state), "application/json")
            return

        self._respond_error(404, "not found")

    def do_POST(self) -> None:
        try:
            body_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._respond_error(400, "invalid content-length")
            return
        raw = self.rfile.read(body_length).decode(ENCODING)
        parsed = urlparse(self.path)

        if parsed.path == "/api/launch-editor":
            import subprocess
            import time as _time
            req = json.loads(raw)
            filename = req.get("filename", "")
            diagram_path = (self.schematic_dir / filename).resolve()
            if not diagram_path.is_relative_to(self.schematic_dir.resolve()) or not diagram_path.exists():
                self._respond_error(404, "diagram not found")
                return
            bridge_script = Path(__file__).parent.parent / "reference" / "mermaid_edit" / "bridge.py"
            proc = subprocess.Popen(
                ["python3", str(bridge_script), str(diagram_path), "--no-browser"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            _time.sleep(2)
            line = (proc.stdout.readline().decode().strip() if proc.stdout else "")
            url = line.split(": ", 1)[1] if ": " in line else ""
            self._respond(json.dumps({"url": url, "pid": proc.pid}), "application/json")
            return

        if parsed.path == "/api/open":
            req = json.loads(raw)
            result = open_in_ide(ide=req.get("ide", "code"), file_path=req.get("path", ""))
            if result == "access denied":
                self._respond_error(403, "access denied")
            else:
                self._respond("ok", "text/plain")
            return

        if parsed.path == "/api/note":
            notes_path = self.schematic_dir / "overview.notes.json"
            try:
                existing = json.loads(notes_path.read_text(encoding=ENCODING)) if notes_path.exists() else []
            except json.JSONDecodeError:
                existing = []
            existing.append(json.loads(raw))
            notes_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond("ok", "text/plain")
            return

        if parsed.path == "/api/question":
            questions_path = self.schematic_dir / "overview.questions.json"
            try:
                existing = json.loads(questions_path.read_text(encoding=ENCODING)) if questions_path.exists() else []
            except json.JSONDecodeError:
                existing = []
            question = json.loads(raw)
            server_idx = len(existing)
            question["idx"] = server_idx
            existing.append(question)
            questions_path.write_text(json.dumps(existing, indent=2), encoding=ENCODING)
            self._respond(json.dumps({"idx": server_idx}), "application/json")
            return

        if parsed.path == "/api/save-file":
            req = json.loads(raw)
            file_name = req.get("name", "")
            content = req.get("content", "")
            file_path = (self.schematic_dir / file_name).resolve()
            if not file_path.is_relative_to(self.schematic_dir.resolve()):
                self._respond_error(403, "access denied")
                return
            file_path.write_text(content, encoding=ENCODING)
            self._respond("ok", "text/plain")
            return

        self._respond_error(404, "not found")

    def _build_manifest(self) -> dict:
        d = self.schematic_dir
        manifest: dict = {"name": d.name, "files": {}, "components": [], "diagrams": [], "research": [], "trace": None}

        for md_file in ["objective.md", "tasks.md"]:
            p = d / md_file
            if p.exists():
                manifest["files"][md_file] = True

        comp_dir = d / "components"
        if comp_dir.exists():
            manifest["components"] = sorted(f.name for f in comp_dir.iterdir() if f.suffix == ".md")

        for mmd in d.glob("*.mmd"):
            manifest["diagrams"].append(mmd.name)

        # Research directory: investigations + traces
        research_dir = d / "research"
        if research_dir.exists():
            manifest["research"] = sorted(
                f.name for f in research_dir.iterdir()
                if f.is_file() and f.suffix == ".md"
            )

        # Multi-trace support: check research/traces/ first, then legacy traces/, then legacy trace/
        traces_dir = research_dir / "traces" if research_dir.exists() else None
        legacy_traces_dir = d / "traces"
        legacy_trace_dir = d / "trace"

        if traces_dir and traces_dir.exists():
            trace_entries: list[dict] = []
            index_path = traces_dir / "_index.json"
            if index_path.exists():
                try:
                    index_data = json.loads(index_path.read_text(encoding=ENCODING))
                    trace_entries = index_data.get("traces", [])
                except json.JSONDecodeError:
                    pass
            if not trace_entries:
                for sub_dir in sorted(traces_dir.iterdir()):
                    if sub_dir.is_dir():
                        trace_entries.append({"name": sub_dir.name, "status": "unknown", "steps": 0})
            manifest["traces"] = trace_entries
            manifest["trace"] = None
        elif legacy_traces_dir.exists():
            trace_entries = []
            index_path = legacy_traces_dir / "_index.json"
            if index_path.exists():
                try:
                    index_data = json.loads(index_path.read_text(encoding=ENCODING))
                    trace_entries = index_data.get("traces", [])
                except json.JSONDecodeError:
                    pass
            if not trace_entries:
                for sub_dir in sorted(legacy_traces_dir.iterdir()):
                    if sub_dir.is_dir():
                        trace_entries.append({"name": sub_dir.name, "status": "unknown", "steps": 0})
            manifest["traces"] = trace_entries
            manifest["trace"] = None
        elif legacy_trace_dir.exists():
            manifest["trace"] = sorted(f.name for f in legacy_trace_dir.iterdir() if f.is_file())
            manifest["traces"] = None
        else:
            manifest["traces"] = None

        notes_path = d / "overview.notes.json"
        if notes_path.exists():
            manifest["notes"] = json.loads(notes_path.read_text(encoding=ENCODING))
        else:
            manifest["notes"] = []

        return manifest

    def _respond(self, content: str, content_type: str) -> None:
        body = content.encode(ENCODING)
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset={ENCODING}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_error(self, code: int, msg: str) -> None:
        body = msg.encode(ENCODING)
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def launch_overview(schematic_dir: Path) -> None:
    # Set project root from schematic location so IDE paths resolve correctly
    search = schematic_dir.resolve()
    while search != search.parent:
        if (search / ".git").exists():
            set_project_root(search)
            break
        search = search.parent

    OverviewHandler.schematic_dir = schematic_dir
    server = ThreadingHTTPServer(("127.0.0.1", 0), OverviewHandler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"

    print(f"Schematic overview: {url}")
    print(f"Schematic: {schematic_dir.name}")
    print("Press Ctrl+C to stop")
    webbrowser.open(url)

    # Watch for questions and answer via claude CLI
    questions_path = schematic_dir / "overview.questions.json"
    answers_path = schematic_dir / "overview.answers.json"

    def question_watcher() -> None:
        seen_count = 0
        while True:
            try:
                if questions_path.exists():
                    questions = json.loads(questions_path.read_text(encoding=ENCODING))
                    if len(questions) > seen_count:
                        for i in range(seen_count, len(questions)):
                            q = questions[i]
                            text = q.get("text", "")
                            if not text:
                                continue
                            server_idx = q.get("idx", i)
                            answered = False
                            if answers_path.exists():
                                answers = json.loads(answers_path.read_text(encoding=ENCODING))
                                answered = any(a.get("idx") == server_idx for a in answers)
                            if not answered:
                                context = q.get("context", "overview")
                                spawn_answer(
                                    question_text=text,
                                    server_idx=server_idx,
                                    context=context,
                                    answers_path=answers_path,
                                )
                        seen_count = len(questions)
            except (json.JSONDecodeError, KeyError):
                pass
            time.sleep(1)

    threading.Thread(target=question_watcher, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        print("\noverview server stopped")
