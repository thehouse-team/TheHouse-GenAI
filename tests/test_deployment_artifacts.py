"""Offline checks for the deployment build artifacts (spec 009, B1/B2).

These tests read the lockfiles, the pyproject, the Docker ignore file and the Dockerfile
as plain text. They never open a socket and never invoke Docker.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
LOCK = REPO_ROOT / "requirements.lock"
DEV_LOCK = REPO_ROOT / "requirements-dev.lock"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
DOCKERFILE = REPO_ROOT / "Dockerfile"

_PINNED = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[A-Za-z0-9._,-]+\])?==([^\s\\]+)")
_SHA256 = re.compile(r"--hash=sha256:[0-9a-f]{64}\b")
_DEV_ONLY = frozenset({"mypy", "pytest", "ruff"})


def _canonical(name: str) -> str:
    """Normalize a distribution name for comparison."""

    return re.sub(r"[-_.]+", "-", name).lower()


def _extras(bracket: str) -> frozenset[str]:
    """Return the normalized extra names declared in a requirement."""

    inner = bracket.strip("[]")
    return frozenset(_canonical(item) for item in inner.split(",") if item.strip())


def _lock_entries(path: Path) -> dict[str, tuple[str, frozenset[str], list[str]]]:
    """Map each pinned distribution to its version, extras and hash lines."""

    entries: dict[str, tuple[str, frozenset[str], list[str]]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _PINNED.match(line)
        if match is not None:
            current = _canonical(match.group(1))
            entries[current] = (match.group(3), _extras(match.group(2) or ""), [])
            continue
        if current is not None and _SHA256.search(line) is not None:
            entries[current][2].append(line.strip())
    return entries


def _pyproject() -> dict[str, object]:
    """Load pyproject.toml as a plain mapping."""

    with PYPROJECT.open("rb") as handle:
        data: object = tomllib.load(handle)
    assert isinstance(data, dict)
    return data


def _direct_requirements(table: object) -> list[tuple[str, frozenset[str]]]:
    """Parse a list of PEP 508 requirement strings into names and extras."""

    assert isinstance(table, list)
    result: list[tuple[str, frozenset[str]]] = []
    for raw in table:
        assert isinstance(raw, str)
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]+\])?", raw)
        assert match is not None
        result.append((_canonical(match.group(1)), _extras(match.group(2) or "")))
    return result


def _runtime_requirements() -> list[tuple[str, frozenset[str]]]:
    """Read the direct runtime dependencies from pyproject.toml."""

    project = _pyproject().get("project")
    assert isinstance(project, dict)
    return _direct_requirements(project.get("dependencies"))


def _dev_requirements() -> list[tuple[str, frozenset[str]]]:
    """Read the direct development dependencies from pyproject.toml."""

    project = _pyproject().get("project")
    assert isinstance(project, dict)
    optional = project.get("optional-dependencies")
    assert isinstance(optional, dict)
    return _direct_requirements(optional.get("dev"))


def test_lock_covers_every_runtime_dependency() -> None:
    entries = _lock_entries(LOCK)
    for name, extras in _runtime_requirements():
        assert name in entries, f"{name} is missing from requirements.lock"
        assert extras <= entries[name][1], f"{name}: extras {sorted(extras)} are not pinned"


def test_lock_excludes_development_only_packages() -> None:
    entries = _lock_entries(LOCK)
    for name in _DEV_ONLY:
        assert name not in entries, f"{name} must not be installed in the runtime image"


def test_pip_tools_is_not_a_project_dependency() -> None:
    assert "pip-tools" not in PYPROJECT.read_text(encoding="utf-8")


def test_dockerignore_is_a_strict_whitelist() -> None:
    lines = [
        stripped
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    ]
    assert lines[0] == "*"
    assert set(lines[1:6]) == {
        "!src/",
        "!src/**",
        "!pyproject.toml",
        "!requirements.lock",
        "!README.md",
    }
    included = {line for line in lines if line.startswith("!")}
    for forbidden in (".env", ".venv", "tests", "specs", ".git", "scripts"):
        assert not any(forbidden in path for path in included)


# --- Four drift checks for the development lockfile -------------------------------


def test_dev_lock_covers_every_direct_dependency() -> None:
    entries = _lock_entries(DEV_LOCK)
    for name, extras in _runtime_requirements() + _dev_requirements():
        assert name in entries, f"{name} is missing from requirements-dev.lock"
        assert extras <= entries[name][1], f"{name}: extras {sorted(extras)} are not pinned"


def test_both_locks_pin_sha256_hashes_for_every_package() -> None:
    for path in (LOCK, DEV_LOCK):
        entries = _lock_entries(path)
        assert entries, f"{path.name} has no pinned packages"
        for name, (_version, _extras, hashes) in entries.items():
            assert hashes, f"{path.name}: {name} has no sha256 hashes"
            for line in hashes:
                assert _SHA256.search(line) is not None, f"{path.name}: {name} bad hash line"


def test_runtime_pins_are_identical_in_both_locks() -> None:
    runtime = _lock_entries(LOCK)
    development = _lock_entries(DEV_LOCK)
    assert runtime, "requirements.lock is empty"
    for name, (version, extras, _hashes) in runtime.items():
        assert name in development, f"{name} missing from requirements-dev.lock"
        dev_version, dev_extras, _dev_hashes = development[name]
        assert version == dev_version, f"{name}: {version} != {dev_version}"
        assert extras == dev_extras, f"{name}: extras {sorted(extras)} != {sorted(dev_extras)}"


def test_dev_only_packages_are_split_between_locks() -> None:
    runtime = _lock_entries(LOCK)
    development = _lock_entries(DEV_LOCK)
    for name in _DEV_ONLY:
        assert name in development, f"{name} missing from requirements-dev.lock"
        assert name not in runtime, f"{name} leaked into requirements.lock"
