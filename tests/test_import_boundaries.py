"""Import boundary and offline suite tests.

The port must stay vendor neutral: no module of the service may import an HTTP client
or a provider SDK, the domain must not depend on the provider package at all and the
application must not depend on a provider implementation.
"""

from __future__ import annotations

import ast
import socket
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src" / "thehouse_genai"
PROJECT_PACKAGE = "thehouse_genai"

FORBIDDEN_IMPORTS = frozenset(
    {
        "httpx",
        "requests",
        "urllib3",
        "aiohttp",
        "socket",
        "openai",
        "anthropic",
        "google",
    }
)

# The Gemini adapter is the only module of the service allowed to speak HTTP. The
# exception is explicit, minimal and keyed by path suffix.
ALLOWED_FORBIDDEN_IMPORTS: dict[str, frozenset[str]] = {
    "providers/gemini.py": frozenset({"httpx"}),
}

PROVIDERS_PACKAGE = f"{PROJECT_PACKAGE}.providers"
PROVIDER_IMPLEMENTATIONS = (
    f"{PROVIDERS_PACKAGE}.fake",
    f"{PROVIDERS_PACKAGE}.factory",
    f"{PROVIDERS_PACKAGE}.gemini",
)
PROVIDER_IMPLEMENTATION_ALIASES = frozenset({"fake", "factory", "gemini"})


def _resolve_module(module: str | None, level: int, package: str) -> str | None:
    """Resolve an import statement to its absolute dotted path."""

    if level == 0:
        return module
    parts = package.split(".")
    base = parts[: len(parts) - (level - 1)]
    if module:
        base = base + module.split(".")
    return ".".join(base)


def _iter_imports(tree: ast.Module, package: str) -> Iterator[tuple[str, str | None]]:
    """Yield every imported module with the name it was bound to, if any."""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, None
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_module(node.module, node.level, package)
            if resolved is None:
                continue
            for alias in node.names:
                if node.level > 0:
                    yield f"{resolved}.{alias.name}", None
                else:
                    yield resolved, alias.name


def _is_provider_import(module: str) -> bool:
    return module == PROVIDERS_PACKAGE or module.startswith(f"{PROVIDERS_PACKAGE}.")


def _is_provider_implementation(module: str, alias: str | None) -> bool:
    if module.startswith(PROVIDER_IMPLEMENTATIONS):
        return True
    return module == PROVIDERS_PACKAGE and alias in PROVIDER_IMPLEMENTATION_ALIASES


def _allowed_roots(file_name: str) -> frozenset[str]:
    """Return the forbidden roots this file is allowed to import."""

    normalized = file_name.replace("\\", "/")
    for suffix, roots in ALLOWED_FORBIDDEN_IMPORTS.items():
        if normalized.endswith(suffix):
            return roots
    return frozenset()


def _display(module: str, alias: str | None) -> str:
    """Return the dotted path of what is actually imported."""

    if module == PROVIDERS_PACKAGE and alias in PROVIDER_IMPLEMENTATION_ALIASES:
        return f"{PROVIDERS_PACKAGE}.{alias}"
    return module


def find_violations(source: str, *, file_name: str, package: str) -> list[str]:
    """Return every forbidden import of a source snippet.

    The message states which file imports what, so a failure is actionable.
    """

    violations: list[str] = []
    allowed = _allowed_roots(file_name)
    for module, alias in _iter_imports(ast.parse(source), package):
        root = module.split(".")[0]
        if root in FORBIDDEN_IMPORTS and root not in allowed:
            violations.append(
                f"{file_name} imports {module}: forbidden dependency on {root}"
            )
        if package.startswith(f"{PROJECT_PACKAGE}.domain") and _is_provider_import(module):
            violations.append(
                f"{file_name} imports {module}: the domain must not depend on providers"
            )
        if package.startswith(f"{PROJECT_PACKAGE}.application") and _is_provider_implementation(
            module, alias
        ):
            violations.append(
                f"{file_name} imports {_display(module, alias)}: "
                "the application must not depend on a provider implementation"
            )
    return violations


def _package_of(path: Path) -> str:
    """Return the package that contains a source file."""

    parts = list(path.relative_to(SOURCE_ROOT.parent).parts)
    return ".".join(parts[:-1])


def _scan_source_tree() -> list[str]:
    violations: list[str] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        violations.extend(
            find_violations(
                source,
                file_name=str(path.relative_to(REPO_ROOT)),
                package=_package_of(path),
            )
        )
    return violations


def test_source_tree_has_no_forbidden_imports() -> None:
    violations = _scan_source_tree()

    assert not violations, "\n".join(violations)


def test_detector_reports_a_forbidden_import() -> None:
    violations = find_violations(
        "import httpx\n",
        file_name="sample/module.py",
        package=f"{PROJECT_PACKAGE}.sample",
    )

    assert violations
    assert "sample/module.py" in violations[0]
    assert "httpx" in violations[0]


def test_detector_reports_a_provider_sdk_import() -> None:
    violations = find_violations(
        "from google import genai\n",
        file_name="sample/module.py",
        package=f"{PROJECT_PACKAGE}.sample",
    )

    assert violations
    assert "google" in violations[0]


def test_detector_reports_a_domain_dependency_on_providers() -> None:
    violations = find_violations(
        "from thehouse_genai.providers.base import GenerativeAiRequest\n",
        file_name="thehouse_genai/domain/sample.py",
        package=f"{PROJECT_PACKAGE}.domain",
    )

    assert violations
    assert "thehouse_genai.providers.base" in violations[0]


def test_detector_reports_an_application_dependency_on_an_implementation() -> None:
    violations = find_violations(
        "from thehouse_genai.providers import fake\n",
        file_name="thehouse_genai/application/sample.py",
        package=f"{PROJECT_PACKAGE}.application",
    )

    assert violations
    assert "fake" in violations[0]


def test_detector_reports_an_application_dependency_on_the_gemini_adapter() -> None:
    violations = find_violations(
        "from thehouse_genai.providers import gemini\n",
        file_name="thehouse_genai/application/sample.py",
        package=f"{PROJECT_PACKAGE}.application",
    )

    assert violations
    assert "gemini" in violations[0]


def test_detector_accepts_httpx_in_the_gemini_adapter() -> None:
    violations = find_violations(
        "import httpx\n",
        file_name="src/thehouse_genai/providers/gemini.py",
        package=f"{PROJECT_PACKAGE}.providers",
    )

    assert not violations


def test_detector_still_rejects_httpx_outside_the_gemini_adapter() -> None:
    violations = find_violations(
        "import httpx\n",
        file_name="src/thehouse_genai/providers/fake.py",
        package=f"{PROJECT_PACKAGE}.providers",
    )

    assert violations
    assert "httpx" in violations[0]


def test_detector_accepts_a_clean_module() -> None:
    violations = find_violations(
        "from thehouse_genai.providers.base import GenerativeAiRequest\n",
        file_name="thehouse_genai/application/sample.py",
        package=f"{PROJECT_PACKAGE}.application",
    )

    assert not violations


def test_network_block_rejects_external_connection() -> None:
    with pytest.raises(RuntimeError, match="network access is forbidden in tests"):
        socket.create_connection(("example.com", 80))


def test_network_block_rejects_external_dns() -> None:
    with pytest.raises(RuntimeError, match="network access is forbidden in tests"):
        socket.getaddrinfo("example.com", 80)


def test_network_block_allows_loopback() -> None:
    assert socket.getaddrinfo("127.0.0.1", 80)
