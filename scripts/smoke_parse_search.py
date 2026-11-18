"""Manual smoke test for parse-search against the real Gemini API.

The script is opt-in and never runs in CI: it refuses when CI is set, requires an
explicit flag and a typed confirmation, and never prints the credential. It reaches the
vendor only through the provider factory and uses the real local moderator with no
daily budget. The corpus contains only synthetic PII and invented moderation tokens.

Usage:
    python scripts/smoke_parse_search.py --i-have-a-real-key --limit 5 --delay 5
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

from thehouse_genai.application.parse_search import ParseSearch
from thehouse_genai.domain.moderation import MAX_TEXT_CHARS as MODERATION_MAX_TEXT_CHARS
from thehouse_genai.domain.search_filters import ParseSearchRequest
from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.factory import build_provider
from thehouse_genai.providers.moderation import GuardedModerationProvider, LocalRuleModerator

CONFIRMATION_WORD: Final[str] = "SI"
CI_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})
CORPUS_PATH: Final[Path] = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "search_query_corpus.json"
)
DEFAULT_DELAY_SECONDS: Final[float] = 5.0
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


class FallbackCollector(logging.Handler):
    """Collect stable fallback reasons emitted by the use case."""

    def __init__(self) -> None:
        super().__init__()
        self.reasons: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        reason = getattr(record, "fallback_reason", None)
        if isinstance(reason, str):
            self.reasons.append(reason)


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


async def _measure(use_case: ParseSearch, case: SmokeCase) -> CaseResult:
    """Run one case through the real use case and compare its filters."""

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
    )


async def _run_all(
    use_case: ParseSearch, cases: tuple[SmokeCase, ...], delay: float
) -> list[CaseResult]:
    """Run every case, pacing calls to stay within the free tier limit."""

    results: list[CaseResult] = []
    for index, case in enumerate(cases):
        if index:
            await asyncio.sleep(delay)
        results.append(await _measure(use_case, case))
    return results


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


def _summary_lines(results: list[CaseResult], reasons: list[str]) -> list[str]:
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
    counts: dict[str, int] = {}
    for reason in reasons:
        counts[reason] = counts.get(reason, 0) + 1
    if counts:
        for reason, count in sorted(counts.items()):
            lines.append(f"| fallback {reason} | {count} |")
    else:
        lines.append("| fallbacks | 0 |")
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
    if not args.yes and not _confirm():
        print("Cancelado: no se ha llamado a la API.")
        return 1
    try:
        settings = _load_settings()
        cases = _load_cases(args.limit)
    except SmokeConfigurationError as exc:
        print(f"Configuración inválida: {exc}")
        return 1
    key_length = len(settings.genai_api_key.get_secret_value()) if settings.genai_api_key else 0
    print("Smoke test de parse-search (capa gratuita, consultas sintéticas)")
    print(f"proveedor: {settings.genai_provider}")
    print(f"modelo: {settings.genai_model}")
    print(f"credencial: presente ({key_length} caracteres)")
    print(f"casos: {len(cases)} | retardo entre llamadas: {args.delay:g} s")
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
    use_case = ParseSearch(provider, moderator=moderator)
    collector = FallbackCollector()
    target = logging.getLogger(PARSE_LOGGER)
    target.addHandler(collector)
    try:
        results = asyncio.run(_run_all(use_case, cases, args.delay))
    finally:
        target.removeHandler(collector)
    for item in results:
        _print_case(item)
    print("")
    print("Resumen para evidence.md")
    print("")
    for line in _summary_lines(results, collector.reasons):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
