# Evidencia — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** IMPLEMENTED (autorización G04 2026-11-15, contrato 003 preservando score ML externo)
- **Fecha:** 2026-11-15
- **Rama:** `feature/smart-match-explanation`

## Comandos y resultados

| Comando | Resultado |
| --- | --- |
| `python -m ruff check .` | PASS |
| `python -m mypy src` | PASS (23 source files) |
| `python -m pytest` | `177 passed, 1 warning` |

## Implementación

- Endpoint protegido: `POST /api/v1/generative/explain-match` (auth servicio `X-Service-Key`, comparación en tiempo constante, 401 sobre estándar).
- Contrato request/response validado con Pydantic (`extra=forbid`): entrada estructurada con `match_score` (0-100, externo) + datos mínimos de property/university/preferences; salida `{"explanation","facts_used"}`.
- GenAI solo redacta: prompt con contexto JSON sanitizado, `system_prompt` explícito (DATA no instrucciones, no cambiar score/ranking, no inventar, español, breve), `facts_used`/fidelidad validados en dominio.
- Validaciones: score preservado (no se recalcula ni se expone modificado), rechazo de campos extra/PII no permitidos por schema, límite de palabras, detección de números/servicios no permitidos en salida, manejo seguro de errores provider (502/503/504/429) sin stack traces ni secretos.
- Fallback: no se fabrica explicación generativa; ante salida inválida/error se responde fallo seguro controlado.

## Pruebas clave

- Auth: sin/incorrecta `X-Service-Key` -> 401.
- Éxito con `FakeProvider`: score/contexto enviados, respuesta estructurada válida.
- Validación entrada: score faltante/fuera de rango y campos extra rechazados (422).
- Fidelidad/guardrails: número inventado y servicio inventado rechazados (502 seguro).
- Prompt injection en `property.title`: no altera contrato ni expone secretos; salida segura validada.
- Errores provider: invalid JSON/invalid response -> 502, timeout -> 504, rate limit -> 429.

## Smoke real

- **PROVIDER-RUNTIME-BLOCKED**: sin `GEMINI_API_KEY`/`GENAI_API_KEY` en entorno; no se ejecutó llamada real a Gemini.
