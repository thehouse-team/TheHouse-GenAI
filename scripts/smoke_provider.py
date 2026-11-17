"""Manual smoke test against the real Gemini API.

The script is opt-in and never runs in CI: it refuses to start when the CI
environment variable is set, it requires an explicit flag and a typed
confirmation, and it never prints the credential. It only uses the provider port,
so it reaches the vendor through the adapter and never speaks HTTP directly.

The prompts use synthetic data of a fictional property: no real data and no PII.

Usage:
    python scripts/smoke_provider.py --i-have-a-real-key
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import statistics
from dataclasses import dataclass
from time import perf_counter
from typing import Final

from thehouse_genai.infrastructure.config import Settings
from thehouse_genai.providers.base import (
    GenerativeAiProvider,
    GenerativeAiRequest,
    ProviderError,
)
from thehouse_genai.providers.factory import build_provider

CONFIRMATION_WORD: Final[str] = "SI"
ITERATIONS: Final[int] = 3
PREVIEW_CHARS: Final[int] = 300
CI_VALUES: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})
DEPRECATION_MESSAGE: Final[str] = "provider.call.deprecation"


class SmokeConfigurationError(RuntimeError):
    """Raised when the environment is not ready to run the smoke test."""


@dataclass(frozen=True)
class SmokeCase:
    """One scenario of the smoke test."""

    name: str
    request: GenerativeAiRequest


@dataclass(frozen=True)
class Measurement:
    """The outcome of one measured call, without any content beyond the preview."""

    duration_ms: float
    input_tokens: int
    output_tokens: int
    finish_reason: str | None
    text: str
    error_code: str | None
    deprecated: bool


class DeprecationWatcher(logging.Handler):
    """Record whether the adapter signalled a deprecation notice."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.deprecated = False

    def emit(self, record: logging.LogRecord) -> None:
        if record.getMessage() == DEPRECATION_MESSAGE:
            self.deprecated = True


def _is_ci() -> bool:
    """Report whether the process runs inside a CI environment."""

    return os.environ.get("CI", "").strip().lower() in CI_VALUES


def _build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""

    parser = argparse.ArgumentParser(
        description="Smoke test manual del proveedor LLM. Nunca lo ejecuta CI."
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
    return parser


def _confirm() -> bool:
    """Ask the operator to type the confirmation word."""

    try:
        answer = input(
            "Vas a llamar a la API real de Gemini con la capa gratuita. "
            f"Escribe {CONFIRMATION_WORD} para confirmar: "
        )
    except EOFError:
        return False
    return answer.strip().upper() == CONFIRMATION_WORD


def _load_settings() -> Settings:
    """Load the settings and check that the smoke test can run.

    Raises:
        SmokeConfigurationError: if the provider, the credential or the model are
            not configured.
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


def _cases() -> tuple[SmokeCase, ...]:
    """Return the scenarios: one Spanish text case and one JSON case."""

    return (
        SmokeCase(
            name="A · texto en español",
            request=GenerativeAiRequest(
                system_prompt=(
                    "Eres un asistente de TheHouse. Respondes en español, de forma breve "
                    "y sin inventar datos que no estén en el texto."
                ),
                prompt=(
                    "Explica en un párrafo breve por qué encajan estos datos con una "
                    "familia que busca vivienda en Málaga. Datos de la vivienda: casa "
                    "de 120 m2, 3 dormitorios, terraza, a 10 minutos del centro y 400 "
                    "euros al mes de comunidad. No añadas datos que no estén aquí."
                ),
                response_format="text",
                temperature=0.2,
                max_output_tokens=400,
            ),
        ),
        SmokeCase(
            name="B · salida JSON",
            request=GenerativeAiRequest(
                system_prompt=(
                    "Eres un asistente de TheHouse. Devuelves solo JSON válido, sin texto "
                    "alrededor."
                ),
                prompt=(
                    "Extrae los datos de esta vivienda ficticia y devuelve un objeto JSON "
                    'con las claves "tipo", "metros", "dormitorios", '
                    '"distancia_al_centro_min" y "comunidad_mensual". Texto: casa de 120 '
                    "m2, 3 dormitorios, terraza, a 10 minutos del centro y 400 euros al "
                    "mes de comunidad."
                ),
                response_format="json",
                temperature=0.0,
                max_output_tokens=400,
            ),
        ),
    )


def _elapsed_ms(started: float) -> float:
    """Return the milliseconds elapsed since the given mark."""

    return round((perf_counter() - started) * 1000, 2)


async def _measure(
    provider: GenerativeAiProvider,
    request: GenerativeAiRequest,
    watcher: DeprecationWatcher,
) -> Measurement:
    """Run one call and keep only its metadata and a short preview."""

    watcher.deprecated = False
    started = perf_counter()
    try:
        response = await provider.generate(request)
    except ProviderError as exc:
        return Measurement(
            duration_ms=_elapsed_ms(started),
            input_tokens=0,
            output_tokens=0,
            finish_reason=None,
            text="",
            error_code=exc.code,
            deprecated=watcher.deprecated,
        )
    return Measurement(
        duration_ms=_elapsed_ms(started),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        finish_reason=response.finish_reason,
        text=response.text,
        error_code=None,
        deprecated=watcher.deprecated,
    )


async def _run_cases(
    provider: GenerativeAiProvider,
    watcher: DeprecationWatcher,
) -> list[tuple[str, list[Measurement]]]:
    """Run every scenario the requested number of times."""

    results: list[tuple[str, list[Measurement]]] = []
    for case in _cases():
        measurements: list[Measurement] = []
        for _ in range(ITERATIONS):
            measurements.append(await _measure(provider, case.request, watcher))
        results.append((case.name, measurements))
    return results


def _preview(text: str) -> str:
    """Return a short preview of an answer."""

    if len(text) <= PREVIEW_CHARS:
        return text
    return f"{text[:PREVIEW_CHARS]}…"


def _summary_row(name: str, measurements: list[Measurement]) -> str:
    """Render one markdown row with the aggregated measurements."""

    if not measurements:
        return f"| {name} | 0 | - | - | - | - | - | - | - | - |"
    durations = [measurement.duration_ms for measurement in measurements]
    successes = [measurement for measurement in measurements if measurement.error_code is None]
    failures = [
        measurement.error_code
        for measurement in measurements
        if measurement.error_code is not None
    ]
    input_tokens = int(statistics.median([m.input_tokens for m in successes])) if successes else 0
    output_tokens = int(statistics.median([m.output_tokens for m in successes])) if successes else 0
    finish_reason = next(
        (measurement.finish_reason for measurement in successes if measurement.finish_reason),
        "-",
    )
    deprecated = "sí" if any(measurement.deprecated for measurement in measurements) else "no"
    errors = ", ".join(sorted({code for code in failures if code})) if failures else "-"
    return (
        f"| {name} | {len(measurements)} | {min(durations):.1f} | "
        f"{statistics.median(durations):.1f} | {max(durations):.1f} | "
        f"{input_tokens} | {output_tokens} | {finish_reason} | {deprecated} | {errors} |"
    )


def main(argv: list[str] | None = None) -> int:
    """Run the manual smoke test and return the process exit code."""

    if _is_ci():
        print("El smoke test manual no se ejecuta en CI.")
        return 2
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.i_have_a_real_key and os.environ.get("GENAI_SMOKE") != "1":
        parser.print_usage()
        print(
            "\nFalta la confirmación opt-in: usa --i-have-a-real-key o GENAI_SMOKE=1."
        )
        return 1
    if not args.yes and not _confirm():
        print("Cancelado: no se ha llamado a la API.")
        return 1
    try:
        settings = _load_settings()
    except SmokeConfigurationError as exc:
        print(f"Configuración inválida: {exc}")
        return 1
    key_length = len(settings.genai_api_key.get_secret_value()) if settings.genai_api_key else 0
    print("Smoke test del proveedor LLM (capa gratuita, prompts sintéticos)")
    print(f"proveedor: {settings.genai_provider}")
    print(f"modelo: {settings.genai_model}")
    print(f"credencial: presente ({key_length} caracteres)")
    watcher = DeprecationWatcher()
    root_logger = logging.getLogger()
    root_logger.addHandler(watcher)
    try:
        provider = build_provider(settings)
        results = asyncio.run(_run_cases(provider, watcher))
    finally:
        root_logger.removeHandler(watcher)
    failed = False
    for name, measurements in results:
        print("")
        print(f"Caso {name}")
        for index, measurement in enumerate(measurements, start=1):
            if measurement.error_code is not None:
                failed = True
                print(
                    f"  iteración {index}: {measurement.duration_ms:.1f} ms | "
                    f"error {measurement.error_code}"
                )
                continue
            print(
                f"  iteración {index}: {measurement.duration_ms:.1f} ms | "
                f"tokens {measurement.input_tokens}/{measurement.output_tokens} | "
                f"finish_reason {measurement.finish_reason}"
            )
        first = next((m for m in measurements if m.error_code is None), None)
        if first is not None:
            print(f"  primera respuesta: {_preview(first.text)}")
    print("")
    print("Resumen para evidence.md")
    print("")
    print(
        "| Caso | Iteraciones | Latencia min (ms) | Latencia mediana (ms) | "
        "Latencia max (ms) | Tokens entrada | Tokens salida | finish_reason | "
        "Aviso de deprecación | Errores |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for name, measurements in results:
        print(_summary_row(name, measurements))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
