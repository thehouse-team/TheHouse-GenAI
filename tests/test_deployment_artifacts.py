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
BICEP = REPO_ROOT / "infra" / "genai.bicep"

_PINNED = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[A-Za-z0-9._,-]+\])?==([^\s\\;]+)"
    r"(?:\s*;\s*([^\\]+?))?\s*\\?\s*$"
)
_SHA256 = re.compile(r"--hash=sha256:[0-9a-f]{64}\b")
_DEV_ONLY = frozenset({"mypy", "pytest", "ruff"})


def _canonical(name: str) -> str:
    """Normalize a distribution name for comparison."""

    return re.sub(r"[-_.]+", "-", name).lower()


def _extras(bracket: str) -> frozenset[str]:
    """Return the normalized extra names declared in a requirement."""

    inner = bracket.strip("[]")
    return frozenset(_canonical(item) for item in inner.split(",") if item.strip())


def _lock_entries(path: Path) -> dict[str, tuple[str, frozenset[str], str, list[str]]]:
    """Map each pin to its version, extras, platform marker and hash lines."""

    entries: dict[str, tuple[str, frozenset[str], str, list[str]]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _PINNED.match(line)
        if match is not None:
            current = _canonical(match.group(1))
            marker = (match.group(4) or "").strip()
            entries[current] = (match.group(3), _extras(match.group(2) or ""), marker, [])
            continue
        if current is not None and _SHA256.search(line) is not None:
            entries[current][3].append(line.strip())
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
    for name, _extras in _runtime_requirements():
        assert name in entries, f"{name} is missing from requirements.lock"


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
    for name, _extras in _runtime_requirements() + _dev_requirements():
        assert name in entries, f"{name} is missing from requirements-dev.lock"


def test_both_locks_pin_sha256_hashes_for_every_package() -> None:
    for path in (LOCK, DEV_LOCK):
        entries = _lock_entries(path)
        assert entries, f"{path.name} has no pinned packages"
        for name, (_version, _extras, _marker, hashes) in entries.items():
            assert hashes, f"{path.name}: {name} has no sha256 hashes"
            for line in hashes:
                assert _SHA256.search(line) is not None, f"{path.name}: {name} bad hash line"


def test_runtime_pins_are_identical_in_both_locks() -> None:
    runtime = _lock_entries(LOCK)
    development = _lock_entries(DEV_LOCK)
    assert runtime, "requirements.lock is empty"
    for name, (version, extras, marker, _hashes) in runtime.items():
        assert name in development, f"{name} missing from requirements-dev.lock"
        dev_version, dev_extras, dev_marker, _dev_hashes = development[name]
        assert version == dev_version, f"{name}: {version} != {dev_version}"
        assert extras == dev_extras, f"{name}: extras {sorted(extras)} != {sorted(dev_extras)}"
        assert marker == dev_marker, f"{name}: marker {marker!r} != {dev_marker!r}"


def test_platform_specific_pins_keep_their_markers() -> None:
    runtime = _lock_entries(LOCK)
    development = _lock_entries(DEV_LOCK)
    assert "uvloop" in runtime, "uvloop must be pinned for non-Windows platforms"
    assert "sys_platform != 'win32'" in runtime["uvloop"][2]
    assert "colorama" in development, "colorama must be pinned for Windows"
    assert "sys_platform == 'win32'" in development["colorama"][2]


def test_uvicorn_standard_transitive_deps_are_pinned() -> None:
    # A universal uv lock flattens extras: uvicorn is pinned without [standard],
    # so the packages contributed by that extra must be pinned explicitly.
    runtime = _lock_entries(LOCK)
    for name in ("uvloop", "watchfiles", "websockets", "httptools", "python-dotenv"):
        assert name in runtime, f"{name} (uvicorn[standard]) is missing from the lock"


def test_dev_only_packages_are_split_between_locks() -> None:
    runtime = _lock_entries(LOCK)
    development = _lock_entries(DEV_LOCK)
    for name in _DEV_ONLY:
        assert name in development, f"{name} missing from requirements-dev.lock"
        assert name not in runtime, f"{name} leaked into requirements.lock"


# --- Text checks for the Dockerfile (B2) ------------------------------------------


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def test_every_from_is_pinned_to_a_64_hex_digest() -> None:
    from_lines = [line for line in _dockerfile().splitlines() if line.startswith("FROM ")]
    assert len(from_lines) >= 2, "Dockerfile must have at least two stages"
    for line in from_lines:
        assert "python:3.12-slim@sha256:" in line, line
        assert re.search(r"@sha256:[0-9a-f]{64}\b", line) is not None, line


def test_dockerfile_is_multistage_and_copies_only_venv_and_src() -> None:
    text = _dockerfile()
    assert re.search(r"^FROM\s+.*\sAS\s+builder\s*$", text, re.MULTILINE) is not None
    assert re.search(r"^FROM\s+.*\sAS\s+runtime\s*$", text, re.MULTILINE) is not None
    assert "COPY --from=builder /opt/venv /opt/venv" in text
    assert "COPY src /app/src" in text
    assert "PYTHONPATH=/app/src" in text


def test_dockerfile_runs_as_non_root_user() -> None:
    text = _dockerfile()
    assert "USER 10001:10001" in text
    assert "USER root" not in text


def test_dockerfile_never_chowns_or_chmods_to_the_app_user() -> None:
    for line in _dockerfile().splitlines():
        if line.startswith(("COPY", "RUN")):
            assert "chown" not in line, line
            assert "chmod" not in line, line
    assert "--chown=10001" not in _dockerfile()


def test_dockerfile_installs_from_the_hash_pinned_lock_only() -> None:
    text = _dockerfile()
    assert "--require-hashes -r requirements.lock" in text
    assert "pip install ." not in text
    assert re.search(r"pip install[^\n]*\s\.\s*$", text, re.MULTILINE) is None
    assert "setuptools" not in text.lower()


def test_uvicorn_suppresses_the_server_header_and_uses_one_worker() -> None:
    text = _dockerfile()
    assert "--no-server-header" in text
    assert '"--workers", "1"' in text


def test_dockerfile_never_copies_forbidden_paths() -> None:
    for line in _dockerfile().splitlines():
        if line.startswith("COPY") and "--from=" not in line:
            lowered = line.lower()
            for forbidden in (".env", "tests", "specs", "scripts"):
                assert forbidden not in lowered, line


def test_dockerfile_has_no_secret_arg_or_env() -> None:
    secret_names = (
        "API_KEY",
        "SERVICE_KEY",
        "METRICS_KEY",
        "SECRET",
        "TOKEN",
        "PASSWORD",
        "CREDENTIAL",
    )
    for line in _dockerfile().splitlines():
        if line.startswith(("ARG ", "ENV ")):
            for name in secret_names:
                assert name not in line, line


def test_dockerfile_has_no_healthcheck_and_exposes_port_8000() -> None:
    text = _dockerfile()
    assert "HEALTHCHECK" not in text
    assert "EXPOSE 8000" in text


def test_dockerfile_sets_python_runtime_flags() -> None:
    text = _dockerfile()
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "PYTHONUNBUFFERED=1" in text


# --- Text checks for the Bicep template (B5) -----------------------------------------


def _bicep() -> str:
    return BICEP.read_text(encoding="utf-8")


def test_bicep_references_existing_environment_and_internal_ingress() -> None:
    text = _bicep()
    assert "Microsoft.App/managedEnvironments@2025-01-01' existing" in text
    assert 'name: \'cae-thehouse-u2\'' in text
    assert "external: false" in text
    assert "targetPort: 8000" in text
    assert "allowInsecure: true" in text


def test_bicep_pins_scale_resources_and_probes() -> None:
    text = _bicep()
    assert "minReplicas: 1" in text
    assert "maxReplicas: 1" in text
    assert "cpu: json('0.25')" in text
    assert "memory: '0.5Gi'" in text
    for probe_type in ("Startup", "Liveness", "Readiness"):
        assert f"type: '{probe_type}'" in text
    assert text.count("path: '/health/live'") == 2
    assert text.count("path: '/health/ready'") == 1


def test_bicep_secrets_are_secure_without_defaults_or_literals() -> None:
    text = _bicep()
    assert text.count("@secure()") == 4
    for name in (
        "genaiApiKey",
        "genaiServiceKey",
        "genaiMetricsKey",
        "genaiServiceKeyPrevious",
    ):
        match = re.search(rf"param {name} string.*$", text, re.MULTILINE)
        assert match is not None, name
        assert "=" not in match.group(0), name
    for env_name in ("GENAI_API_KEY", "GENAI_SERVICE_KEY", "GENAI_METRICS_KEY"):
        match = re.search(rf"name: '{env_name}', secretRef:", text)
        assert match is not None, env_name


def test_bicep_image_is_a_digest_parameter_without_registry_credentials() -> None:
    text = _bicep()
    assert "param imageDigest string" in text
    assert "image: imageDigest" in text
    assert "registries:" not in text
    assert "GENAI_PROVIDER', value: 'gemini'" in text
    assert "GENAI_MODEL', value: 'gemini-3.5-flash-lite'" in text
    assert "application: 'thehouse-genai'" in text
    assert "environment: 'production'" in text


def test_apt_packages_are_version_pinned_and_cache_cleaned() -> None:
    text = _dockerfile()
    if "apt-get" not in text:
        return
    assert "--no-install-recommends" in text
    assert "rm -rf /var/lib/apt/lists/*" in text
    block = text.split("apt-get install", 1)[1].split("\n\n", 1)[0]
    packages = re.findall(r"(?m)^\s+([a-z][a-z0-9+:.=~\-]*)\s*\\?\s*$", block)
    assert packages, "no apt packages found in the install block"
    for package in packages:
        assert "=" in package, f"apt package {package} is not version-pinned"
    assert any(package.startswith("zlib1g=") for package in packages)
