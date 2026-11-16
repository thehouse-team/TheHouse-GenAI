# Evidencia — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** IMPLEMENTED (extendida por autorización G02/G03 2026-11-15)
- **Fecha:** 2026-11-15
- **Rama:** `feature/smart-match-explanation`

## Comandos y resultados (esta ejecución)

| Comando | Resultado |
| --- | --- |
| `python -m ruff check .` | `All checks passed!` |
| `python -m mypy src` | `Success: no issues found in 23 source files` |
| `python -m pytest` | `177 passed, 1 warning in 1.38s` |

## Alcance ejecutado bajo autorización explícita

- Se mantuvo el puerto `GenerativeAiProvider`, DTOs, taxonomía y guard central.
- Se extendió configuración/factory para soportar `fake` y `gemini` (selección validada, sin SDK).
- Se implementó `GeminiGenerativeAiProvider` (httpx, timeout, retries acotados, mapeo de errores, parsing/validación de respuesta, sin exponer secretos/raw errors).
- `FakeProvider` sigue disponible para tests (sin red). Tests automatizados no consumen API real.
- Variables/credenciales: `GEMINI_API_KEY` o `GENAI_API_KEY` vía entorno/Settings (`SecretStr`), `.env.example` actualizado con placeholders.
- Smoke real Gemini: **PROVIDER-RUNTIME-BLOCKED** (no se detectó `GEMINI_API_KEY`/`GENAI_API_KEY` en entorno; no se inventó credencial ni se activó billing). Se realizó prueba de adaptador con transporte simulado/httpx mock en tests.

## Cost control (COST-001)

- Modelo inicial preferido: `gemini-2.5-flash-lite` (configurable; sin fallback automático a modelos pagos).
- Solo generación textual, sin grounding/web/tools externas.
- Límites: timeout, `GENAI_MAX_INPUT_CHARS`, `GENAI_MAX_OUTPUT_TOKENS/CHARS`, retries acotados (`GENAI_MAX_RETRIES`).
- Sin tarjeta/billing/infra nueva.
