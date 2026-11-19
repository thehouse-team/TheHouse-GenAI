"""Guards of the manual smoke test.

The script is a local utility: it must never run in CI, it must require an explicit
opt-in and no test of the suite may import it.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = REPO_ROOT / "tests"
SCRIPT_PATH = REPO_ROOT / "scripts" / "smoke_provider.py"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _run_script(*args: str, ci: str = "") -> subprocess.CompletedProcess[str]:
    """Run the smoke script in a subprocess, without any provider credential."""

    env = {**os.environ, "CI": ci}
    env.pop("GENAI_SMOKE", None)
    return subprocess.run(  # noqa: S603 - static interpreter and static arguments
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def test_smoke_script_exists_outside_the_test_suite() -> None:
    assert SCRIPT_PATH.is_file()
    assert TESTS_ROOT not in SCRIPT_PATH.parents


def test_ci_workflow_never_runs_the_smoke_script() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    # The container smoke step is part of spec 009; CI must never invoke the
    # manual, opt-in script from 011 (the "scripts/" guard enforces that).
    assert "scripts/" not in workflow


def test_pytest_only_collects_the_tests_directory() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")

    assert 'testpaths = ["tests"]' in pyproject


def test_script_refuses_to_run_in_ci() -> None:
    result = _run_script("--i-have-a-real-key", ci="true")

    assert result.returncode == 2
    assert "CI" in result.stdout
    assert "proveedor" not in result.stdout


def test_script_requires_the_opt_in_flag() -> None:
    result = _run_script(ci="")

    assert result.returncode == 1
    assert "--i-have-a-real-key" in result.stdout


def test_script_does_not_import_http_clients() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "httpx" not in source
    assert "requests" not in source
    assert "aiohttp" not in source


def test_script_never_prints_the_credential() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "get_secret_value()" in source
    assert "print(settings.genai_api_key" not in source
    assert "print(key" not in source


def _imports_the_script(source: str) -> bool:
    """Report whether a source imports the smoke script as a module."""

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[-1] == "smoke_provider" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[-1] == "smoke_provider":
                return True
    return False


def test_no_test_imports_the_smoke_script() -> None:
    offenders: list[str] = []
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if path.name == "test_smoke_script.py":
            continue
        source = path.read_text(encoding="utf-8")
        if _imports_the_script(source):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())

    assert offenders == []
