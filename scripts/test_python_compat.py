#!/usr/bin/env python3
"""Regression tests for Python 3.10+ import compatibility.

Catches the bug fixed in PR (forthcoming) where `reference/agent_responder.py`
used PEP 604 union syntax (`threading.Lock | None`) in function signatures
without `from __future__ import annotations`. On Python >= 3.10, this caused:

    TypeError: unsupported operand type(s) for |:
               'builtin_function_or_method' and 'NoneType'

because `threading.Lock` is a `builtin_function_or_method` (alias for
`_thread.allocate_lock`), not a class — so `threading.Lock | None` fails
at runtime evaluation even on Python 3.12.

See: https://github.com/Meeks91/Schematic/issues/1
"""
import importlib
import importlib.machinery
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
REFERENCE_DIR = REPO_ROOT / "reference"


def _load_module(name: str, path: Path) -> object:
    """Load a module from a path (handles extensionless 'schematic' CLI script)."""
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise ImportError(f"Cannot create spec for {name} at {path}")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class TestPythonImportCompat(unittest.TestCase):
    """Every schematic module must import cleanly on the running Python version.

    PEP 604 unions in function signatures require either `from __future__
    import annotations` OR operands that are classes (not builtins like
    `threading.Lock`). This test catches both classes of regression.
    """

    MODULES = [
        # (name, path, is_directory_with_init)
        ("schematic.agent_responder", REFERENCE_DIR / "agent_responder.py", False),
        ("schematic.shared_utils", REFERENCE_DIR / "shared_utils.py", False),
        ("schematic_cli", SCRIPTS_DIR / "schematic", False),
        ("schematic.track", SCRIPTS_DIR / "track.py", False),
    ]

    def test_all_modules_import(self) -> None:
        """Every CLI/module imports without TypeError on Python 3.10+."""
        # Ensure reference/ is on sys.path so `from agent_responder import ...` works
        sys.path.insert(0, str(REFERENCE_DIR))

        for name, path, _ in self.MODULES:
            with self.subTest(module=name):
                try:
                    _load_module(name, path)
                except TypeError as e:
                    if "unsupported operand type" in str(e):
                        self.fail(
                            f"Module `{name}` failed to import: PEP 604 union in "
                            f"function signature without `from __future__ import "
                            f"annotations`. Add the future import to "
                            f"`{path.relative_to(REPO_ROOT)}`. Original error: {e}"
                        )
                    raise

    def test_agent_responder_specific_bug(self) -> None:
        """The exact line that caused the original issue.

        Before the fix, `file_lock: threading.Lock | None = None` raised
        TypeError at module import on Python 3.10+.
        """
        sys.path.insert(0, str(REFERENCE_DIR))
        # Reload to force fresh evaluation
        if "agent_responder" in sys.modules:
            del sys.modules["agent_responder"]

        try:
            importlib.import_module("agent_responder")
        except TypeError as e:
            if "threading.Lock" in str(e) or "builtin_function_or_method" in str(e):
                self.fail(
                    "agent_responder.py regressed: `threading.Lock | None` "
                    "without `from __future__ import annotations` causes "
                    f"TypeError at import time. Error: {e}"
                )
            raise

    def test_overview_module_loads(self) -> None:
        """`overview.py` (the dashboard launcher) must load without error.

        It imports agent_responder, so this is a transitive test for the
        full import chain that breaks when the bug regresses.
        """
        # Path setup for overview.py's lazy imports
        sys.path.insert(0, str(SCRIPTS_DIR))
        sys.path.insert(0, str(REFERENCE_DIR))

        try:
            loader = importlib.machinery.SourceFileLoader(
                "schematic.overview", str(SCRIPTS_DIR / "overview.py")
            )
            spec = importlib.util.spec_from_loader("schematic.overview", loader)
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
        except TypeError as e:
            if "unsupported operand type" in str(e):
                self.fail(
                    "scripts/overview.py regressed on import — the dashboard "
                    "cannot launch. Original error: " + str(e)
                )
            raise


if __name__ == "__main__":
    unittest.main()