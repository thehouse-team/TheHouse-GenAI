# Plan — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** IMPLEMENTED (plan aprobado el 2026-11-18)
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  005-security, 006-moderation, 007-observability, 011-llm-provider

## Enfoque técnico

1. Definir un schema cerrado de request, filtros y respuesta con aliases camelCase y
   `extra="forbid"`, incluyendo `maxDistanceKm` y `promptVersion`.
2. Extraer el guard de texto de 003 a `domain/text_guard.py` con re-exports, sin tocar
   el contrato de `explain-match`.
3. Construir extractores deterministas de dinero, distancia, universidad, servicios y
   mascotas, y `redact_pii` reutilizando las regex de `domain/moderation.py`.
4. Pedir al proveedor solo `{"filters": {...}}` con `response_format="json"` y validar
   cada filtro contra la evidencia del query; podar lo no respaldado.
5. Calcular `confidence` de forma determinista; ante cualquier fallo responder 200 con
   filtros vacíos, `generated=false` y `low` (nunca 502).
6. Moderar entrada y salida, reutilizar auth, rate limit, presupuesto, métricas y
   `safetySettings`, y añadir la ruta cerrada `parse-search` a las métricas.
7. Probar con fake provider, corpus versionado y script manual opt-in, 100% sin red.

## Pasos previstos (bloques)

- **B0 (docs):** activar 004; reescribir spec/plan/task/checklist/evidence; actualizar
  `memoria.md`, `AGENTS.md` y `README.md`; gates y commit documental.
- **B1 (dominio):** contratos, extractores, `redact_pii` y guard compartido con re-exports.
- **B2 (guardrails):** validación anti-alucinación y cálculo de `confidence`.
- **B3 (caso de uso):** prompt `parse_search_v1`, proveedor, fallback, presupuesto y
  métricas.
- **B4 (moderación y PII):** moderación de entrada/salida y redacción end-to-end.
- **B5 (HTTP y observabilidad):** endpoint, enums de métricas, ruta cerrada y logs.
- **B6 (corpus):** fixture versionado, pruebas parametrizadas y script manual opt-in.
- **B7 (cierre):** evidence, memoria, gates, PR con squash y estado `IMPLEMENTED`.

## Archivos previstos

**Nuevos en `src/`:** `domain/search_filters.py`, `domain/text_guard.py`,
`application/parse_search.py`.

**Modificados en `src/`:** `domain/match_explanation.py` y
`application/explain_match.py` (re-exports del guard, sin cambio de contrato),
`application/metrics_port.py`, `infrastructure/logging.py`,
`api/routes/generative.py`, `infrastructure/config.py` (solo si hace falta).

**Nuevos en `tests/`:** `test_domain_search_filters.py`, `test_search_text_guard.py`,
`test_parse_search_guardrails.py`, `test_parse_search.py`,
`test_parse_search_moderation.py`, `test_parse_search_pii.py`,
`test_parse_search_api.py`, `test_search_query_corpus.py`,
`test_smoke_parse_search.py`, `fixtures/search_query_corpus.json`.

**Modificados en `tests/`:** `test_http_metrics.py`, `test_observability_leak_checks.py`,
`test_import_boundaries.py`, `test_smoke_script.py` (solo si hace falta).

**Documentación:** los 5 archivos de `specs/004-*`, `memoria.md`, `AGENTS.md`, `README.md`.

## Estrategia de pruebas

- Contrato: aliases camelCase, `extra="forbid"`, longitudes y decimales.
- Extracción: `$3,000`, `3 mil`, `3.5 mil`, `3k`, `menos de 3000`, `entre 2000 y 3000`
  → 3000; `2026`, `1.3 km`, teléfono de 10 dígitos y `3 km` no son dinero.
- Distancia: `1.3 km`, `2 kilómetros`, `a menos de 2 km`; minutos y cuadras → `null`.
- Universidad: alias UTTT, nombre completo, sin evidencia → poda.
- Servicios y mascotas: sinónimos, `mascotas` fuera de servicios, negativo → `null`.
- PII: correo/teléfono/URL redactados antes del prompt, sin falsos positivos de precios.
- Inyección: delimitación, escape, homoglifos y ancho cero; nunca rechazo.
- Moderación: bloqueo de entrada sin proveedor; bloqueo/review de salida; errores.
- Fallos del proveedor, timeout, JSON inválido y presupuesto → 200 vacío + `low`.
- HTTP: 401, 422 (vacía/oversized), 429 con `Retry-After`, `X-Request-ID`, headers.
- Corpus versionado (28 frases + 2 de contrato) con fake provider; sin red.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| El modelo inventa filtros | Poda por evidencia del texto; `generated=false` si no queda ninguno. |
| El modelo controla `confidence` o `generated` | El completion solo permite `filters`; `extra="forbid"`. |
| PII llega a Gemini | Redacción con las regex de 006 antes del prompt; test de ausencia en el prompt. |
| Inyección en la query | Delimitación, escape, detección y log; `safetySettings` ya existentes. |
| `mascotas` duplicado en servicios y `petsAllowed` | Vocabulario de servicios lo excluye. |
| Otra moneda | Descartar `maxBudget` y `currency`, bajar confianza, sin conversión. |
| Métricas distorsionadas | Añadir `EndpointPath.PARSE_SEARCH` y enums cerrados nuevos. |
| `request_id` no correlacionado en el caso de uso | Registrar el filtro para `application.parse_search`. |
| Contrato en borrador | Decisiones D1–D13 ratificadas antes de B1. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde, sin red.
- Evidencia registrada, sin secretos, PII ni caracteres CJK.
- PR a `main` con squash y el checklist SDD; solo entonces estado `IMPLEMENTED`.
