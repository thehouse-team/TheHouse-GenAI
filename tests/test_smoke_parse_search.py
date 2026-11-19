"""Guards of the manual parse-search smoke test.

The script is a local utility: it must never run in CI, it must require an explicit
opt-in, no test of the suite may import it, and it must never print the credential.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from thehouse_genai.domain.text_guard import contains_injection_marker

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = REPO_ROOT / "tests"
SCRIPT_PATH = REPO_ROOT / "scripts" / "smoke_parse_search.py"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
CORPUS_PATH = TESTS_ROOT / "fixtures" / "search_query_corpus.json"


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


def test_corpus_exists_next_to_the_tests() -> None:
    assert CORPUS_PATH.is_file()


def test_ci_workflow_never_runs_the_smoke_script() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "smoke" not in workflow
    assert "scripts/" not in workflow


def test_pytest_only_collects_the_tests_directory() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")

    assert 'testpaths = ["tests"]' in pyproject


def test_script_refuses_to_run_in_ci() -> None:
    result = _run_script("--i-have-a-real-key", ci="true")

    assert result.returncode == 2
    assert "CI" in result.stdout
    assert "credencial" not in result.stdout


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
            if any(alias.name.split(".")[-1] == "smoke_parse_search" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[-1] == "smoke_parse_search":
                return True
    return False


def test_no_test_imports_the_smoke_script() -> None:
    offenders: list[str] = []
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if path.name == "test_smoke_parse_search.py":
            continue
        source = path.read_text(encoding="utf-8")
        if _imports_the_script(source):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())

    assert offenders == []


_FAILING_PROVIDER_SETUP = """
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import ProviderUnavailableError

class _FailingProvider:
    async def generate(self, request):
        logging.getLogger("thehouse_genai.providers.gemini").warning(
            "provider.call.failed",
            extra={
                "error_code": "PROVIDER_UNAVAILABLE",
                "vendor_detail": "DETALLE_PROHIBIDO_123",
            },
        )
        raise ProviderUnavailableError()

mod.build_provider = lambda settings: _FailingProvider()
mod._load_settings = lambda: Settings(
    _env_file=None, app_env="test", genai_provider="fake"
)
"""


_INVALID_JSON_SETUP = """
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import GenerativeAiResponse, GenerativeAiUsage

class _InvalidJsonProvider:
    async def generate(self, request):
        text = (
            "Resultado: " + chr(96) * 3 + "json" + chr(10)
            + '{"filters": {"essentialServices": "internet", "extraKey": 1}, "confidence": "high"}'
            + chr(10) + chr(96) * 3
        )
        return GenerativeAiResponse(
            text=text,
            usage=GenerativeAiUsage(input_tokens=1, output_tokens=1),
        )

mod.build_provider = lambda settings: _InvalidJsonProvider()
mod._load_settings = lambda: Settings(
    _env_file=None, app_env="test", genai_provider="fake"
)
"""


_INJECTION_SETUP = """
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import GenerativeAiResponse, GenerativeAiUsage

class _OkProvider:
    async def generate(self, request):
        return GenerativeAiResponse(
            text='{"filters": {"university": "UTTT"}}',
            usage=GenerativeAiUsage(input_tokens=1, output_tokens=1),
        )

mod.build_provider = lambda settings: _OkProvider()
mod._load_settings = lambda: Settings(
    _env_file=None, app_env="test", genai_provider="fake"
)
"""


def _run_with_fake(
    setup: str, *args: str, ci: str = ""
) -> subprocess.CompletedProcess[str]:
    """Run the script with an offline provider, without importing it in the suite."""

    wrapper = (
        "import importlib.util, logging, sys\n"
        "from pathlib import Path\n"
        f"ROOT = Path({str(REPO_ROOT)!r})\n"
        "spec = importlib.util.spec_from_file_location(\n"
        "    'smoke_parse_search', ROOT / 'scripts' / 'smoke_parse_search.py'\n"
        ")\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "sys.modules['smoke_parse_search'] = mod\n"
        "spec.loader.exec_module(mod)\n"
        f"{setup}\n"
        f"raise SystemExit(mod.main({list(args)!r}))\n"
    )
    env = {**os.environ, "CI": ci}
    env.pop("GENAI_SMOKE", None)
    return subprocess.run(  # noqa: S603 - static interpreter, offline wrapper
        [sys.executable, "-c", wrapper],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def test_help_documents_the_error_stop_option() -> None:
    result = _run_script("--help", ci="")

    assert result.returncode == 0
    assert "--stop-after-errors" in result.stdout


def test_failure_reports_bounded_code_and_fallback_reason() -> None:
    result = _run_with_fake(
        _FAILING_PROVIDER_SETUP,
        "--i-have-a-real-key",
        "--yes",
        "--limit",
        "1",
        "--delay",
        "0",
        "--stop-after-errors",
        "1",
    )

    assert result.returncode == 0, result.stderr
    assert "codigo=PROVIDER_UNAVAILABLE" in result.stdout
    assert "fallback_reason=PROVIDER_ERROR" in result.stdout
    assert "| error de proveedor PROVIDER_UNAVAILABLE | 1 |" in result.stdout
    assert "| fallback PROVIDER_ERROR | 1 |" in result.stdout
    assert "Detenido: 1 fallos de proveedor consecutivos." in result.stdout
    assert "provider.call.failed" not in result.stdout
    assert "parse_search.fallback" not in result.stdout
    assert "DETALLE_PROHIBIDO_123" not in result.stdout


def test_default_stop_after_three_consecutive_errors() -> None:
    result = _run_with_fake(
        _FAILING_PROVIDER_SETUP,
        "--i-have-a-real-key",
        "--yes",
        "--limit",
        "6",
        "--delay",
        "0",
    )

    assert result.returncode == 0
    for case_id in ("ps-01", "ps-02", "ps-03"):
        assert case_id in result.stdout
    assert "ps-04" not in result.stdout
    assert "Detenido: 3 fallos de proveedor consecutivos." in result.stdout


def test_only_runs_the_requested_case() -> None:
    result = _run_with_fake(
        _FAILING_PROVIDER_SETUP,
        "--i-have-a-real-key",
        "--yes",
        "--only",
        "ps-04",
        "--delay",
        "0",
        "--stop-after-errors",
        "1",
    )

    assert result.returncode == 0, result.stderr
    assert "ps-04:" in result.stdout
    assert "ps-01:" not in result.stdout
    assert "| casos totales | 1 |" in result.stdout


def test_diagnose_reports_types_and_keys_for_invalid_json() -> None:
    result = _run_with_fake(
        _INVALID_JSON_SETUP,
        "--i-have-a-real-key",
        "--yes",
        "--only",
        "ps-01",
        "--delay",
        "0",
        "--diagnose",
    )

    assert result.returncode == 0, result.stderr
    assert "diagnostico INVALID_JSON" in result.stdout
    assert "filters.essentialServices: list_type" in result.stdout
    assert "filters.extraKey: extra_forbidden" in result.stdout
    assert "claves raiz: filters=object, confidence=string" in result.stdout
    assert "claves filters: essentialServices=string, extraKey=number" in result.stdout
    assert "envuelto_en_texto=si | bloque_de_codigo=si" in result.stdout
    assert "Resultado:" not in result.stdout
    assert '{"filters"' not in result.stdout
    assert "parse_search.fallback" not in result.stdout


def test_injection_detection_line_is_silent_in_the_console() -> None:
    result = _run_with_fake(
        _INJECTION_SETUP,
        "--i-have-a-real-key",
        "--yes",
        "--only",
        "ps-27",
        "--delay",
        "0",
    )

    case = next(
        item
        for item in json.loads(
            CORPUS_PATH.read_text(encoding="utf-8")
        )["cases"]
        if item["id"] == "ps-27"
    )
    assert contains_injection_marker(case["query"]) is True

    assert result.returncode == 0, result.stderr
    assert "ps-27:" in result.stdout
    assert "parse_search.injection_detected" not in result.stdout


def test_diagnose_is_silent_for_non_json_failures() -> None:
    result = _run_with_fake(
        _FAILING_PROVIDER_SETUP,
        "--i-have-a-real-key",
        "--yes",
        "--only",
        "ps-01",
        "--delay",
        "0",
        "--diagnose",
    )

    assert result.returncode == 0, result.stderr
    assert "diagnostico INVALID_JSON" not in result.stdout
