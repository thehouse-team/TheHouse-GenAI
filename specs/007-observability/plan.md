# Plan — 007-observability Observabilidad

- **Estado:** ACTIVE
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  005-security, 006-moderation, 011-llm-provider
- **Plan aprobado:** 2026-11-18 (decisiones 1–9 en `memoria.md`)

## Enfoque técnico

1. Documentar el schema de logs (apéndice A de `spec.md`) y no ampliar la allowlist salvo
   el `request_id` ya permitido, inyectado por un `logging.Filter` desde el `ContextVar`.
2. Definir en `application/metrics_port.py` las etiquetas como enums cerrados, el Protocol
   `MetricsRecorder` y los tipos inmutables del snapshot; `infrastructure/metrics.py`
   implementa el puerto con `threading.Lock`, reloj inyectable y contadores/histograma.
3. Instrumentar el middleware HTTP (peticiones, status, latencia) y el caso de uso
   (proveedor, tokens, fallback, moderación) desde una única fuente de verdad.
4. Añadir el presupuesto diario con offset UTC-6 fijo, `Decimal` para el coste y
   `BUDGET_EXHAUSTED` como fallback de log/métrica, sin tocar contratos.
5. Exponer `GET /internal/metrics` y `GET /internal/health/detail` en JSON con clave
   separada `GENAI_METRICS_KEY`, sin rate limit y con el sobre de error estándar.
6. Definir SLOs y alertas documentadas para G10 (apéndice B); sin APM ni dashboards aquí.

## Pasos previstos (bloques)

- **B0 (docs):** activar la spec y actualizar SDD con el alcance, dependencias, schema,
  SLOs, limitaciones y decisiones. Gates y commit documental.
- **B1 (núcleo):** `application/metrics_port.py` + `infrastructure/metrics.py` +
  `tests/test_metrics_registry.py`.
- **B2 (HTTP):** instrumentación del middleware y del normalize de rutas.
- **B3 (aplicación):** instrumentación de `ExplainMatch` y filtro de `request_id`.
- **B4 (presupuesto):** `Settings`, `DailyBudget`, coste y `BUDGET_EXHAUSTED`.
- **B5 (endpoints):** rutas internas protegidas y esquema JSON estable.
- **B6 (no-fuga):** pruebas de ausencia de contenido y de cardinalidad.
- **B7 (cierre):** evidencia, gates, revisión de seguridad y commit de cierre.

## Archivos previstos

Nuevos:

- `src/thehouse_genai/application/metrics_port.py`
- `src/thehouse_genai/infrastructure/metrics.py`
- `src/thehouse_genai/infrastructure/budget.py` (B4)
- `src/thehouse_genai/api/routes/internal.py` (B5)
- `tests/test_metrics_registry.py`, `tests/test_http_metrics.py`,
  `tests/test_observability.py`, `tests/test_budget.py`,
  `tests/test_internal_endpoints.py`, `tests/test_observability_leak_checks.py`

Modificados: `memoria.md`, los cinco archivos del SDD de 007, `api/app.py`,
`api/middleware.py`, `api/auth.py`, `api/rate_limit.py`, `application/explain_match.py`,
`infrastructure/config.py`, `infrastructure/logging.py`, `.env.example` (B4).

**No se crea** `infrastructure/tracing.py`: la correlación se resuelve con `request_id`.
No se añade ninguna dependencia a `pyproject.toml`, incluido `tzdata`.

## Estrategia de pruebas

- Contadores: incrementos, acumulación por conjunto de etiquetas, rechazo de nombres y
  etiquetas inválidos, concurrencia básica.
- Histograma: conteo de buckets y desbordamiento, media y percentiles con datos conocidos.
- Snapshot: orden determinista, independencia del estado vivo, tipado inmutable y
  serialización JSON sin `NaN`/`Infinity`.
- Integración: 200/401/413/422/429 en el middleware; `generated` y `fallback_reason` en
  el caso de uso; presupuesto sin llamada al proveedor al agotarse.
- No-fuga: marcadores únicos inyectados como título, completion y clave, ausentes en logs
  y en el snapshot; `test_import_boundaries.py` debe seguir verde.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| PII en métricas | etiquetas de enum cerrado; snapshot solo con agregados |
| Cardinalidad explosiva | rutas acotadas, status acotados, sin IDs ni request IDs |
| Coste de observabilidad | contadores 100% y locks de corta duración |
| Doble conteo del proveedor | única fuente de verdad en el caso de uso |
| Presupuesto multi-instancia | documentado; G10 con cupo global compartido |
| Días de cuota no alineados | offset UTC-6 + nota sobre medianoche Pacífico |
| Alertas ruidosas | umbrales iniciales y recalibración en staging |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde, sin red.
- Evidencia registrada, sin secretos y con revisión de seguridad.
- Solo entonces se cambia el estado a `IMPLEMENTED` y 004 pasa a `ACTIVE` en G08.
