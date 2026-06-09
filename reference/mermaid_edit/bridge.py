import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EDITOR_HTML = Path(__file__).parent / "editor.html"
CONTENT_PATH = "/content"
SAVE_PATH = "/save"
ENCODING = "utf-8"


class MermaidBridgeHandler(BaseHTTPRequestHandler):  # stdlib request-handler subclass — Handler suffix is the framework convention here
    diagram_path: Path
    on_saved: threading.Event

    def do_GET(self) -> None:
        if self.path == CONTENT_PATH:
            self._respond(
                content=self.diagram_path.read_text(encoding=ENCODING),
                content_type="text/plain",
            )
            return
        self._respond(
            content=EDITOR_HTML.read_text(encoding=ENCODING),
            content_type="text/html",
        )

    def do_POST(self) -> None:
        body_length = int(self.headers["Content-Length"])
        edited_diagram = self.rfile.read(body_length).decode(ENCODING)
        self.diagram_path.write_text(edited_diagram, encoding=ENCODING)
        self._respond(content="ok", content_type="text/plain")
        self.on_saved.set()

    def _respond(self, content: str, content_type: str) -> None:
        body = content.encode(ENCODING)
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset={ENCODING}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def launch_editor(diagram_path: Path) -> None:
    MermaidBridgeHandler.diagram_path = diagram_path
    MermaidBridgeHandler.on_saved = threading.Event()

    server = ThreadingHTTPServer(("127.0.0.1", 0), MermaidBridgeHandler)
    editor_url = f"http://127.0.0.1:{server.server_address[1]}/"

    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Mermaid editor: {editor_url}", flush=True)
    webbrowser.open(editor_url)

    MermaidBridgeHandler.on_saved.wait()
    server.shutdown()
    print(f"Saved: {diagram_path}", flush=True)


if __name__ == "__main__":
    launch_editor(diagram_path=Path(sys.argv[1]))
