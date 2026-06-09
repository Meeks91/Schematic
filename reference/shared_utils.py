"""Shared utilities for the schematic UI skill."""
import shutil
import subprocess
from pathlib import Path

_project_root_override: Path | None = None


def set_project_root(root: Path) -> None:
    global _project_root_override
    _project_root_override = root.resolve()


def resolve_project_root() -> Path:
    if _project_root_override:
        return _project_root_override
    search = Path.cwd().resolve()
    while search != search.parent:
        if (search / ".git").exists():
            return search
        search = search.parent
    return Path.cwd().resolve()


def open_in_ide(ide: str, file_path: str) -> str:
    if not file_path:
        return "ok"

    project_root = resolve_project_root()
    clean_file = file_path.split(":")[0]

    candidate = Path(clean_file)
    if candidate.is_absolute() and candidate.exists():
        full_path = candidate
    else:
        full_path = (project_root / clean_file).resolve()

    if not full_path.is_relative_to(project_root):
        return "access denied: path outside project"

    if not full_path.exists():
        return f"file not found: {full_path}"

    line = file_path.split(":")[1] if ":" in file_path else "1"
    if not line.isdigit():
        line = "1"

    if ide == "vscode":
        cmd = ["code", "--goto", f"{full_path}:{line}"]
    else:
        idea_bin = shutil.which("idea")
        if not idea_bin:
            return "idea not found on PATH"
        cmd = [idea_bin, "--line", line, str(full_path)]

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return "ok"
