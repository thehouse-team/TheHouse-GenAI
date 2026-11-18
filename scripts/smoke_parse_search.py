"""Manual smoke test for parse-search against the real Gemini API.

The script is opt-in and never runs in CI: it refuses when CI is set, requires an
explicit flag and a typed confirmation, and never prints the credential. It reaches the
vendor only through the provider factory and uses the real local moderator with no
daily budget. The corpus contains only synthetic PII and invented moderation tokens.

The ``--diagnose`` flag is opt-in: for INVALID_JSON fallbacks it reports validation
error types and locations, key names and JSON types only, never values or the response.

Usage:
    python scripts/smoke_parse_search.py --i-have-a-real-key --limit 5 --delay 5
    python scripts/smoke_parse_search.py --i-have-a-real-key --only ps-03 --diagnose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import statistics
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Final, cast

from pydantic import ValidationError

from thehouse_genai.application.metrics_port import FallbackReason, ProviderErrorCode
from thehouse_genai.application.parse_search import ParseSearch
from thehouse_genai.domain.moderation import MAX_TEXT_CHARS as MODERATION_MAX_TEXT_CHARS
from thehouse_genai.domain.search_filters import ParseSearchRequest, RawParseSearchCompletion
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    GenerativeAiResponse,
    ProviderError,
)
from thehouse_genai.providers.factory import build_provider
from thehouse_genai.providers.moderation import GuardedModerationProvider, LocalRuleModerator

CONFIRMATION_WORD: Final[str] = "SI"
CI_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})
CORPUS_PATH: Final[Path] = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "search_query_corpus.json"
)
DEFAULT_DELAY_SECONDS: Final[float] = 5.0
DEFAULT_STOP_AFTER_ERRORS: Final[int] = 3
PROVIDER_LOGGER: Final[str] = "thehouse_genai.providers.gemini"
FAILURE_EVENT: Final[str] = "provider.call.failed"
FALLBACK_EVENT: Final[str] = "parse_search.fallback"
INJECTION_EVENT: Final[str] = "parse_search.injection_detected"
HIDDEN_EVENTS: Final[frozenset[str]] = frozenset(
    {FAILURE_EVENT, FALLBACK_EVENT, INJECTION_EVENT}
)
CODE_FENCE: Final[str] = "```"
MAX_KEY_CHARS: Final[int] = 40
PROVIDER_CODES: Final[frozenset[str]] = frozenset(item.value for item in ProviderErrorCode)
FALLBACK_CODES: Final[frozenset[str]] = frozenset(item.value for item in FallbackReason)
FILTER_FIELDS: Final[tuple[str, ...]] = (
    "maxBudget",
    "currency",
    "maxDistanceKm",
    "university",
    "essentialServices",
    "petsAllowed",
)
PARSE_LOGGER: Final[str] = "thehouse_genai.application.parse_search"


class SmokeConfigurationError(RuntimeError):
    """Raised when the environment or the corpus is not ready to run."""


@dataclass(frozen=True)
class SmokeCase:
    """One versioned query and its expected filters."""

    case_id: str
    query: str
    expected_filters: dict[str, object]


@dataclass(frozen=True)
class CaseResult:
    """The outcome of one case, with bounded comparison metadata only."""

    case_id: str
    obtained_filters: dict[str, object]
    confidence: str
    generated: bool
    duration_ms: float
    field_matches: tuple[tuple[str, bool], ...]
    exact: bool
    provider_error_codes: tuple[str, ...] = ()
    fallback_reasons: tuple[str, ...] = ()
    diagnostic: tuple[str, ...] = ()

    @property
    def failed(self) -> bool:
        """Report whether the provider failed for this case."""

        return bool(self.provider_error_codes)


class FallbackCollector(logging.Handler):
    """Collect stable fallback reasons emitted by the use case."""

    def __init__(self) -> None:
        super().__init__()
        self.reasons: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        reason = getattr(record, "fallback_reason", None)
        if isinstance(reason, str):
            self.reasons.append(reason)


class ProviderErrorCollector(logging.Handler):
    """Collect only bounded error codes from provider failure records."""

    def __init__(self) -> None:
        super().__init__()
        self.codes: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.getMessage() != FAILURE_EVENT:
            return
        code = getattr(record, "error_code", None)
        if isinstance(code, str):
            self.codes.append(_bounded(code, PROVIDER_CODES))


class _SkipFailureLineFilter(logging.Filter):
    """Hide only the raw provider and fallback lines from console handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage() not in HIDDEN_EVENTS


@dataclass(frozen=True)
class _LogCleanup:
    """Everything needed to restore the logging configuration after the run."""

    added: tuple[logging.Handler, ...]
    filtered: tuple[logging.Handler, ...]
    silence: logging.Filter


def _bounded(value: object, allowed: frozenset[str]) -> str:
    """Keep only a known bounded label, never free-form detail."""

    text = str(value)
    return text if text in allowed else "UNKNOWN"


def _silence_failure_line() -> _LogCleanup:
    """Drop the raw failure line from console output; keep every other log record."""

    root = logging.getLogger()
    silence = _SkipFailureLineFilter()
    existing: tuple[logging.Handler, ...] = tuple(root.handlers)
    added: tuple[logging.Handler, ...] = ()
    if not existing:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(console)
        added = (console,)
    for handler in (*existing, *added):
        handler.addFilter(silence)
    return _LogCleanup(added=added, filtered=existing, silence=silence)


def _restore_logging(cleanup: _LogCleanup) -> None:
    """Restore the handlers and filters changed for the smoke run."""

    root = logging.getLogger()
    for handler in (*cleanup.filtered, *cleanup.added):
        handler.removeFilter(cleanup.silence)
    for handler in cleanup.added:
        root.removeHandler(handler)


class _RecordingProvider:
    """Keep completion texts in memory for opt-in diagnostics; never print them."""

    def __init__(self, delegate: GenerativeAiProvider) -> None:
        self._delegate = delegate
        self.texts: list[str] = []

    async def generate(self, request: GenerativeAiRequest) -> GenerativeAiResponse:
        try:
            response = await self._delegate.generate(request)
        except ProviderError:
            self.texts.append("")
            raise
        self.texts.append(response.text)
        return response


def _json_type(value: object) -> str:
    """Name the JSON type of a value without revealing the value itself."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _safe_key(value: object) -> str:
    """Bound a key name so a model cannot turn it into a full response dump."""

    printable = "".join(char if char.isprintable() else " " for char in str(value))
    return printable[:MAX_KEY_CHARS]


def _validation_errors(text: str) -> tuple[str, ...]:
    """Re-run the existing strict completion model and keep only error type and path."""

    try:
        RawParseSearchCompletion.model_validate_json(text)
    except ValidationError as exc:
        return tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['type']}"
            for item in exc.errors()
        )
    return ()


def _load_json_for_diagnosis(text: str) -> tuple[object | None, bool, bool]:
    """Parse keys from a possibly wrapped completion; report wrapping flags."""

    stripped = text.strip()
    code_block = CODE_FENCE in stripped
    candidate = stripped
    if code_block:
        lines = [
            line for line in stripped.splitlines() if not line.lstrip().startswith(CODE_FENCE)
        ]
        candidate = "\n".join(lines).strip()
    wrapped = not (candidate.startswith("{") or candidate.startswith("["))
    try:
        return json.loads(candidate), wrapped, code_block
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(candidate[start : end + 1]), True, code_block
        except json.JSONDecodeError:
            pass
    return None, wrapped, code_block


def _diagnostic_lines(text: str) -> tuple[str, ...]:
    """Render an INVALID_JSON diagnosis: types and keys only, never values."""

    payload, wrapped, code_block = _load_json_for_diagnosis(text)
    # Validate the extracted object: the wrapper itself would only yield json_invalid.
    parseable = json.dumps(payload) if payload is not None else text
    errors = _validation_errors(parseable)
    lines = [
        "  diagnostico INVALID_JSON:",
        f"    errores: {', '.join(errors) or 'ninguno'}",
    ]
    if isinstance(payload, dict):
        root = ", ".join(
            f"{_safe_key(key)}={_json_type(value)}" for key, value in payload.items()
        )
        lines.append(f"    claves raiz: {root or 'vacias'}")
        filters = payload.get("filters")
        if isinstance(filters, dict):
            nested = ", ".join(
                f"{_safe_key(key)}={_json_type(value)}" for key, value in filters.items()
            )
            lines.append(f"    claves filters: {nested or 'vacias'}")
        else:
            lines.append(f"    claves filters: no disponibles ({_json_type(filters)})")
    else:
        lines.append("    claves raiz: no disponibles")
        lines.append("    claves filters: no disponibles")
    lines.append(
        f"    envuelto_en_texto={'si' if wrapped else 'no'} | "
        f"bloque_de_codigo={'si' if code_block else 'no'}"
    )
    return tuple(lines)


def _is_ci() -> bool:
    """Report whether the process runs inside a CI environment."""

    return os.environ.get("CI", "").strip().lower() in CI_VALUES


def _build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""

    parser = argparse.ArgumentParser(
        description="Smoke test manual de parse-search. Nunca lo ejecuta CI."
    )
    parser.add_argument(
        "--i-have-a-real-key",
        action="store_true",
        help="confirmación explícita de que hay una credencial real configurada",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="omite la confirmación interactiva",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="número de casos a ejecutar (por defecto, todo el corpus)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="segundos entre llamadas (por defecto, 5 para respetar la capa gratuita)",
    )
    parser.add_argument(
        "--stop-after-errors",
        type=int,
        default=DEFAULT_STOP_AFTER_ERRORS,
        help="fallos de proveedor seguidos que detienen la corrida (por defecto, 3)",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="ejecuta solo el caso con este id del corpus",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="en INVALID_JSON, imprime tipos y claves, nunca valores",
    )
    return parser


def _confirm() -> bool:
    """Ask the operator to type the confirmation word."""

    try:
        answer = input(
            "Vas a llamar a la API real de Gemini con consultas sintéticas. "
            f"Escribe {CONFIRMATION_WORD} para confirmar: "
        )
    except EOFError:
        return False
    return answer.strip().upper() == CONFIRMATION_WORD


def _load_settings() -> Settings:
    """Load settings and check that the smoke test can run.

    Raises:
        SmokeConfigurationError: if the provider, credential or model are missing.
    """

    settings = Settings()
    if settings.genai_provider != "gemini":
        raise SmokeConfigurationError("GENAI_PROVIDER debe ser 'gemini'")
    if (
        settings.genai_api_key is None
        or not settings.genai_api_key.get_secret_value().strip()
    ):
        raise SmokeConfigurationError("GENAI_API_KEY no está configurada")
    if settings.genai_model is None or not settings.genai_model.strip():
        raise SmokeConfigurationError("GENAI_MODEL no está configurado")
    return settings


def _case_from_raw(value: object) -> SmokeCase:
    """Validate one raw corpus entry without trusting its shape."""

    if not isinstance(value, dict):
        raise SmokeConfigurationError("entrada de corpus inválida")
    case_id = value.get("id")
    query = value.get("query")
    expected = value.get("expectedFilters")
    if (
        not isinstance(case_id, str)
        or not isinstance(query, str)
        or not isinstance(expected, dict)
    ):
        raise SmokeConfigurationError("caso de corpus incompleto")
    return SmokeCase(case_id, query, cast(dict[str, object], expected))


def _load_cases(limit: int | None) -> tuple[SmokeCase, ...]:
    """Read the versioned corpus and select the requested number of cases.

    Raises:
        SmokeConfigurationError: if the corpus cannot be read or has the wrong version.
    """

    try:
        payload: object = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeConfigurationError("no se pudo leer el corpus") from exc
    if not isinstance(payload, dict) or payload.get("version") != "1.0":
        raise SmokeConfigurationError("el corpus no tiene la versión 1.0")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise SmokeConfigurationError("el corpus no tiene casos")
    selected = raw_cases if limit is None else raw_cases[:limit]
    return tuple(_case_from_raw(item) for item in selected)


def _elapsed_ms(started: float) -> float:
    """Return the milliseconds elapsed since the given mark."""

    return round((perf_counter() - started) * 1000, 2)


async def _measure(
    use_case: ParseSearch,
    case: SmokeCase,
    provider_errors: ProviderErrorCollector,
    fallbacks: FallbackCollector,
    recorder: _RecordingProvider,
    diagnose: bool,
) -> CaseResult:
    """Run one case through the real use case and compare its filters."""

    provider_errors.codes.clear()
    fallbacks.reasons.clear()
    recorder.texts.clear()
    started = perf_counter()
    response = await use_case.execute(
        ParseSearchRequest.model_validate({"query": case.query})
    )
    duration_ms = _elapsed_ms(started)
    body: dict[str, object] = response.model_dump(mode="json", by_alias=True)
    filters = cast(dict[str, object], body["filters"])
    field_matches = tuple(
        (field, filters.get(field) == case.expected_filters.get(field))
        for field in FILTER_FIELDS
    )
    return CaseResult(
        case_id=case.case_id,
        obtained_filters=filters,
        confidence=str(body["confidence"]),
        generated=bool(body["generated"]),
        duration_ms=duration_ms,
        field_matches=field_matches,
        exact=all(matched for _, matched in field_matches),
        provider_error_codes=tuple(provider_errors.codes),
        fallback_reasons=tuple(
            _bounded(reason, FALLBACK_CODES) for reason in fallbacks.reasons
        ),
        diagnostic=(
            _diagnostic_lines(recorder.texts[0])
            if diagnose
            and "INVALID_JSON" in fallbacks.reasons
            and recorder.texts
            else ()
        ),
    )


async def _run_all(
    use_case: ParseSearch,
    cases: tuple[SmokeCase, ...],
    delay: float,
    stop_after_errors: int,
    provider_errors: ProviderErrorCollector,
    fallbacks: FallbackCollector,
    recorder: _RecordingProvider,
    diagnose: bool,
) -> tuple[list[CaseResult], bool]:
    """Run every case, pacing calls and stopping after consecutive provider errors."""

    results: list[CaseResult] = []
    consecutive = 0
    for index, case in enumerate(cases):
        if index:
            await asyncio.sleep(delay)
        result = await _measure(
            use_case, case, provider_errors, fallbacks, recorder, diagnose
        )
        results.append(result)
        consecutive = consecutive + 1 if result.failed else 0
        if consecutive >= stop_after_errors:
            return results, True
    return results, False


def _print_case(result: CaseResult) -> None:
    """Print the per-case result without any query or prompt content."""

    by_field = ", ".join(
        f"{field}={'si' if matched else 'no'}" for field, matched in result.field_matches
    )
    print(
        f"{result.case_id}: filtros={result.obtained_filters} | "
        f"confianza={result.confidence} | generated={result.generated} | "
        f"{result.duration_ms:.1f} ms | exacto={'si' if result.exact else 'no'} | "
        f"campos: {by_field}"
    )
    if result.failed:
        codes = ",".join(result.provider_error_codes)
        reasons = ",".join(result.fallback_reasons) or "-"
        print(f"  fallo de proveedor: codigo={codes} | fallback_reason={reasons}")


def _summary_lines(results: list[CaseResult]) -> list[str]:
    """Render the markdown summary ready to paste into evidence.md."""

    durations = [item.duration_ms for item in results]
    exact = sum(1 for item in results if item.exact)
    lines = [
        "| Métrica | Valor |",
        "| --- | --- |",
        f"| casos totales | {len(results)} |",
        f"| coincidencias exactas | {exact} |",
    ]
    for field in FILTER_FIELDS:
        matched = sum(1 for item in results if dict(item.field_matches)[field])
        lines.append(f"| coincidencia campo {field} | {matched}/{len(results)} |")
    reason_counts: dict[str, int] = {}
    code_counts: dict[str, int] = {}
    for item in results:
        for reason in item.fallback_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        for code in item.provider_error_codes:
            code_counts[code] = code_counts.get(code, 0) + 1
    if reason_counts:
        for reason, count in sorted(reason_counts.items()):
            lines.append(f"| fallback {reason} | {count} |")
    else:
        lines.append("| fallbacks | 0 |")
    if code_counts:
        for code, count in sorted(code_counts.items()):
            lines.append(f"| error de proveedor {code} | {count} |")
    else:
        lines.append("| errores de proveedor | 0 |")
    if durations:
        lines.append(f"| latencia min (ms) | {min(durations):.1f} |")
        lines.append(f"| latencia mediana (ms) | {statistics.median(durations):.1f} |")
        lines.append(f"| latencia max (ms) | {max(durations):.1f} |")
    else:
        lines.extend(
            [
                "| latencia min (ms) | - |",
                "| latencia mediana (ms) | - |",
                "| latencia max (ms) | - |",
            ]
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    """Run the manual smoke test and return the process exit code."""

    if _is_ci():
        print("El smoke test manual no se ejecuta en CI.")
        return 2
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.i_have_a_real_key and os.environ.get("GENAI_SMOKE") != "1":
        parser.print_usage()
        print("\nFalta la confirmación opt-in: usa --i-have-a-real-key o GENAI_SMOKE=1.")
        return 1
    if args.limit is not None and args.limit < 1:
        parser.error("--limit debe ser al menos 1")
    if args.delay < 0:
        parser.error("--delay no puede ser negativo")
    if args.stop_after_errors < 1:
        parser.error("--stop-after-errors debe ser al menos 1")
    if not args.yes and not _confirm():
        print("Cancelado: no se ha llamado a la API.")
        return 1
    try:
        settings = _load_settings()
        cases = _load_cases(args.limit)
    except SmokeConfigurationError as exc:
        print(f"Configuración inválida: {exc}")
        return 1
    if args.only:
        cases = tuple(case for case in cases if case.case_id == args.only)
        if not cases:
            print(f"Caso no encontrado en el corpus: {args.only}")
            return 1
    key_length = len(settings.genai_api_key.get_secret_value()) if settings.genai_api_key else 0
    print("Smoke test de parse-search (capa gratuita, consultas sintéticas)")
    print(f"proveedor: {settings.genai_provider}")
    print(f"modelo: {settings.genai_model}")
    print(f"credencial: presente ({key_length} caracteres)")
    print(
        f"casos: {len(cases)} | retardo entre llamadas: {args.delay:g} s | "
        f"parada tras {args.stop_after_errors} fallos seguidos"
    )
    try:
        provider = build_provider(settings)
    except ValueError as exc:
        print(f"Configuración inválida: {exc}")
        return 1
    moderator = GuardedModerationProvider(
        LocalRuleModerator(),
        timeout_seconds=settings.genai_timeout_seconds,
        max_text_chars=MODERATION_MAX_TEXT_CHARS,
    )
    recorder = _RecordingProvider(provider)
    use_case = ParseSearch(recorder, moderator=moderator)
    fallbacks = FallbackCollector()
    provider_errors = ProviderErrorCollector()
    parse_target = logging.getLogger(PARSE_LOGGER)
    provider_target = logging.getLogger(PROVIDER_LOGGER)
    parse_target.addHandler(fallbacks)
    provider_target.addHandler(provider_errors)
    cleanup = _silence_failure_line()
    try:
        results, stopped = asyncio.run(
            _run_all(
                use_case,
                cases,
                args.delay,
                args.stop_after_errors,
                provider_errors,
                fallbacks,
                recorder,
                args.diagnose,
            )
        )
    finally:
        _restore_logging(cleanup)
        parse_target.removeHandler(fallbacks)
        provider_target.removeHandler(provider_errors)
    for item in results:
        _print_case(item)
        for line in item.diagnostic:
            print(line)
    if stopped:
        print(f"\nDetenido: {args.stop_after_errors} fallos de proveedor consecutivos.")
    print("")
    print("Resumen para evidence.md")
    print("")
    for line in _summary_lines(results):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
