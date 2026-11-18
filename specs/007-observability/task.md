# Tareas — 007-observability Observabilidad

- **Estado:** IMPLEMENTED
- **Plan aprobado:** 2026-11-18 (decisiones 1–9 en `memoria.md`)

> Todas las tareas tienen evidencia real en `evidence.md`.

## B0 — Diseño y activación

- [x] Activar 007 en `memoria.md` y en los cinco archivos del SDD.
- [x] Ampliar dependencias a 001, 002, 003, 005, 006 y 011.
- [x] Documentar esquema de logs, SLOs, alertas G10, limitaciones y decisiones 1–9.
- [x] Gates en verde y commit `docs: activate spec 007 observability`.

## B1 — Núcleo de métricas

- [x] `application/metrics_port.py`: enums cerrados, `MetricsRecorder`, snapshot inmutable.
- [x] `infrastructure/metrics.py`: `MetricsRegistry` con lock, reloj inyectable,
      contadores e histograma con p50/p95 aproximados.
- [x] `tests/test_metrics_registry.py`: incrementos, etiquetas inválidas, histograma,
      percentiles, concurrencia, snapshot y JSON.
- [x] Verificar `test_import_boundaries.py`.

## B2 — Instrumentación HTTP

- [x] Medir peticiones, status y latencia por endpoint normalizado.

## B3 — Instrumentación de aplicación y correlación

- [x] Medir llamadas al proveedor, tokens, `generated`, `fallback_reason` y moderación.
- [x] Inyectar `request_id` en logs por filtro, sin enviarlo a Gemini.

## B4 — Presupuesto diario

- [x] `Settings` con límite de llamadas, límites de tokens y tarifas de coste.
- [x] `DailyBudget` con UTC-6 fijo, consumo controlado y `BUDGET_EXHAUSTED`.
- [x] Coste estimado con `Decimal`; sin dependencias nuevas.

## B5 — Endpoints internos

- [x] `GET /internal/metrics` y `GET /internal/health/detail` con `GENAI_METRICS_KEY`.
- [x] Sin `provider_model`, sin contenido, sin stack traces.

## B6 — No-fuga

- [x] Pruebas de ausencia de contenido, credenciales y PII en logs y métricas.
- [x] Cardinalidad acotada y fronteras de imports reforzadas.

## B7 — Pruebas y cierre

- [x] SLOs y alertas documentados para G10 (sin implementación de APM).
- [x] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [x] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [x] Revisar seguridad y ausencia de secretos/PII.
- [x] Cambiar el estado a `IMPLEMENTED` al cumplir todo.
