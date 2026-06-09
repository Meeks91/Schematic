"""schematic track — Feature flow tracer subcommand.

Lazy-loaded: only imported when `schematic track` is invoked.
Creates trace directory scaffold and validates trace output.
The actual tracing is performed by the agent (Claude) following the flow.

Supports multiple named traces per schematic under `traces/<name>/`.
"""

import json
import re
from pathlib import Path

TRACES_DIR = "research/traces"
LEGACY_TRACE_DIR = "research/trace"
INDEX_FILENAME = "_index.json"
TRACE_FILES = ["trace.json", "trace.mmd", "trace.paths.json", "trace.md"]
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

STATUS_COMPLETE = "complete"
STATUS_PENDING = "pending"

DEFAULT_TRACE_NAME = "default"


def _traces_root(schematic_dir: Path) -> Path:
    return schematic_dir / TRACES_DIR


def _trace_dir(schematic_dir: Path, trace_name: str) -> Path:
    return _traces_root(schematic_dir) / trace_name


def _index_path(schematic_dir: Path) -> Path:
    return _traces_root(schematic_dir) / INDEX_FILENAME


def _load_index(schematic_dir: Path) -> dict:
    path = _index_path(schematic_dir)
    if path.exists():
        return json.loads(path.read_text())
    return {"traces": []}


def _save_index(schematic_dir: Path, index: dict) -> None:
    path = _index_path(schematic_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2) + "\n")


def _find_trace_in_index(index: dict, trace_name: str) -> dict | None:
    for trace_entry in index["traces"]:
        if trace_entry["name"] == trace_name:
            return trace_entry
    return None


def _migrate_legacy_trace(schematic_dir: Path) -> None:
    """Migrate old-style trace/ dir to traces/default/ if needed."""
    legacy_dir = schematic_dir / LEGACY_TRACE_DIR
    traces_root = _traces_root(schematic_dir)

    if not legacy_dir.exists():
        return
    if traces_root.exists():
        return

    traces_root.mkdir(parents=True, exist_ok=True)
    default_dir = traces_root / DEFAULT_TRACE_NAME
    legacy_dir.rename(default_dir)

    entry = "unknown"
    step_count = 0
    status = STATUS_PENDING
    trace_json_path = default_dir / "trace.json"
    if trace_json_path.exists():
        try:
            data = json.loads(trace_json_path.read_text())
            entry = data.get("entry", "unknown")
            steps = data.get("steps", [])
            step_count = len(steps)
            if step_count > 0:
                status = STATUS_COMPLETE
        except json.JSONDecodeError:
            pass

    index = {
        "traces": [
            {
                "name": DEFAULT_TRACE_NAME,
                "entry": entry,
                "status": status,
                "steps": step_count,
            },
        ],
    }
    _save_index(schematic_dir, index)
    print(f"migrated legacy trace/ → traces/{DEFAULT_TRACE_NAME}/")


def _ensure_traces_dir(schematic_dir: Path) -> None:
    """Ensure traces/ exists, migrating legacy trace/ if needed."""
    _migrate_legacy_trace(schematic_dir)


def cmd_track_init(schematic_dir: Path, entry: str, trace_name: str) -> None:
    _ensure_traces_dir(schematic_dir)

    if not KEBAB_CASE_RE.match(trace_name):
        print(f"error: trace name must be kebab-case, got: {trace_name}")
        raise SystemExit(1)

    target_dir = _trace_dir(schematic_dir, trace_name)
    if target_dir.exists():
        print(f"error: trace already exists: {target_dir}")
        raise SystemExit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    meta = {"entry": entry, "status": STATUS_PENDING, "steps": []}
    (target_dir / "trace.json").write_text(json.dumps(meta, indent=2) + "\n")

    index = _load_index(schematic_dir)
    index["traces"].append({
        "name": trace_name,
        "entry": entry,
        "status": STATUS_PENDING,
        "steps": 0,
    })
    _save_index(schematic_dir, index)

    print(f"trace scaffolded: {target_dir}")
    print(f"entry point: {entry}")
    print()
    print("Agent instructions:")
    print(f"  1. Read the entry point: {entry}")
    print("  2. Follow the execution chain (calls, routes, processors)")
    print("  3. For each step record: id, name, type, condition, dataSources, transformation, file")
    print(f"  4. Write results to: {target_dir}/trace.json")
    print(f"  5. Generate mermaid: {target_dir}/trace.mmd")
    print(f"  6. Generate paths map: {target_dir}/trace.paths.json")
    print(f"  7. Generate reference: {target_dir}/trace.md")
    print()
    print("Step types: entry | processor | enrichment | predicate | output | route")


def _validate_single_trace(trace_dir: Path, trace_name: str) -> list[str]:
    """Validate a single trace directory. Returns list of error strings."""
    errors: list[str] = []

    if not trace_dir.exists():
        errors.append(f"trace directory not found: {trace_dir}")
        return errors

    for fname in TRACE_FILES:
        if not (trace_dir / fname).exists():
            errors.append(f"[{trace_name}] missing: {fname}")

    trace_json_path = trace_dir / "trace.json"
    data: dict = {}
    if trace_json_path.exists():
        try:
            data = json.loads(trace_json_path.read_text())
            if "steps" not in data:
                errors.append(f"[{trace_name}] trace.json missing 'steps' array")
            elif len(data["steps"]) == 0:
                errors.append(f"[{trace_name}] trace.json has 0 steps (still pending?)")
            else:
                for i, step in enumerate(data["steps"]):
                    for field in ["id", "name", "type", "file"]:
                        if field not in step:
                            errors.append(f"[{trace_name}] step {i} missing required field: {field}")
        except json.JSONDecodeError as e:
            errors.append(f"[{trace_name}] trace.json invalid JSON: {e}")

    paths_json_path = trace_dir / "trace.paths.json"
    if paths_json_path.exists():
        try:
            paths = json.loads(paths_json_path.read_text())
            if not isinstance(paths, dict):
                errors.append(f"[{trace_name}] trace.paths.json must be a JSON object")
        except json.JSONDecodeError as e:
            errors.append(f"[{trace_name}] trace.paths.json invalid JSON: {e}")

    mmd_path = trace_dir / "trace.mmd"
    if mmd_path.exists():
        content = mmd_path.read_text().strip()
        if not content.startswith("flowchart") and not content.startswith("graph"):
            errors.append(f"[{trace_name}] trace.mmd doesn't start with 'flowchart' or 'graph'")

    return errors


def _refresh_index(schematic_dir: Path) -> None:
    """Re-read all trace dirs and update _index.json with current state."""
    traces_root = _traces_root(schematic_dir)
    if not traces_root.exists():
        return

    index = _load_index(schematic_dir)
    name_to_entry: dict[str, dict] = {
        entry["name"]: entry for entry in index["traces"]
    }

    for sub_dir in sorted(traces_root.iterdir()):
        if not sub_dir.is_dir():
            continue
        trace_name = sub_dir.name
        trace_json_path = sub_dir / "trace.json"
        if not trace_json_path.exists():
            continue

        step_count = 0
        entry_point = "unknown"
        status = STATUS_PENDING
        try:
            data = json.loads(trace_json_path.read_text())
            entry_point = data.get("entry", "unknown")
            steps = data.get("steps", [])
            step_count = len(steps)
            if step_count > 0:
                status = STATUS_COMPLETE
        except json.JSONDecodeError:
            pass

        if trace_name in name_to_entry:
            name_to_entry[trace_name]["steps"] = step_count
            name_to_entry[trace_name]["status"] = status
            name_to_entry[trace_name]["entry"] = entry_point
        else:
            name_to_entry[trace_name] = {
                "name": trace_name,
                "entry": entry_point,
                "status": status,
                "steps": step_count,
            }

    index["traces"] = [
        name_to_entry[name] for name in sorted(name_to_entry.keys())
    ]
    _save_index(schematic_dir, index)


def cmd_track_validate(schematic_dir: Path, trace_name: str | None = None) -> tuple[bool, list[str]]:
    _ensure_traces_dir(schematic_dir)

    traces_root = _traces_root(schematic_dir)
    if not traces_root.exists():
        errors = ["no traces directory found — run `schematic track init` first"]
        print("trace validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return False, errors

    all_errors: list[str] = []

    if trace_name:
        target_dir = _trace_dir(schematic_dir, trace_name)
        all_errors = _validate_single_trace(trace_dir=target_dir, trace_name=trace_name)
    else:
        trace_dirs = sorted(
            d for d in traces_root.iterdir()
            if d.is_dir()
        )
        if not trace_dirs:
            all_errors.append("no trace subdirectories found")
        for sub_dir in trace_dirs:
            trace_errors = _validate_single_trace(
                trace_dir=sub_dir,
                trace_name=sub_dir.name,
            )
            all_errors.extend(trace_errors)

    _refresh_index(schematic_dir)

    if all_errors:
        print("trace validation FAILED:")
        for e in all_errors:
            print(f"  - {e}")
        return False, all_errors

    index = _load_index(schematic_dir)
    total_steps = sum(t["steps"] for t in index["traces"])
    trace_count = len(index["traces"])
    print(f"trace validation PASSED ({trace_count} traces, {total_steps} total steps)")
    return True, []


def cmd_track_show(schematic_dir: Path, trace_name: str | None = None) -> None:
    _ensure_traces_dir(schematic_dir)

    traces_root = _traces_root(schematic_dir)
    if not traces_root.exists():
        print("no traces found — run `schematic track init` first")
        return

    _refresh_index(schematic_dir)
    index = _load_index(schematic_dir)

    if trace_name:
        trace_entry = _find_trace_in_index(index, trace_name)
        if trace_entry is None:
            print(f"trace not found: {trace_name}")
            return
        _show_single_trace(schematic_dir, trace_name)
    else:
        _show_all_traces(index, schematic_dir)


def _show_single_trace(schematic_dir: Path, trace_name: str) -> None:
    """Display detailed steps for a single trace."""
    trace_json_path = _trace_dir(schematic_dir, trace_name) / "trace.json"

    if not trace_json_path.exists():
        print(f"no trace.json found for: {trace_name}")
        return

    try:
        data = json.loads(trace_json_path.read_text())
    except json.JSONDecodeError as e:
        print(f"trace.json is malformed: {e}")
        return

    steps = data.get("steps", [])

    print(f"trace: {trace_name}")
    print(f"entry: {data.get('entry', '?')}")
    print(f"steps: {len(steps)}")
    print()

    for step in steps:
        sid = step.get("id", "?")
        name = step.get("name", "?")
        stype = step.get("type", "?")
        condition = step.get("condition")
        sources = step.get("dataSources", [])
        cond_str = f" [if {condition}]" if condition else ""
        src_str = f" ← {', '.join(sources)}" if sources else ""
        print(f"  {sid}. [{stype}] {name}{cond_str}{src_str}")


def _show_all_traces(index: dict, schematic_dir: Path) -> None:
    """Display summary table of all traces."""
    traces = index.get("traces", [])
    if not traces:
        print("no traces registered")
        return

    print(f"traces: {len(traces)}")
    print()
    print(f"  {'Name':<30} {'Status':<10} {'Steps':<6} Entry")
    print(f"  {'─' * 30} {'─' * 10} {'─' * 6} {'─' * 40}")

    for trace_entry in traces:
        name = trace_entry["name"]
        status_icon = "✓" if trace_entry["status"] == STATUS_COMPLETE else "○"
        status_display = f"{status_icon} {trace_entry['status']}"
        step_count = str(trace_entry["steps"])
        entry = trace_entry.get("entry", "?")
        print(f"  {name:<30} {status_display:<10} {step_count:<6} {entry}")
