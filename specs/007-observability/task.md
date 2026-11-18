# Tareas — 007-observability Observabilidad

- **Estado:** ACTIVE
- **Plan aprobado:** 2026-11-18 (decisiones 1–9 en `memoria.md`)

> No marcar como completada ninguna tarea sin evidencia real en `evidence.md`.

## B0 — Diseño y activación

- [x] Activar 007 en `memoria.md` y en los cinco archivos del SDD.
- [x] Ampliar dependencias a 001, 002, 003, 005, 006 y 011.
- [x] Documentar esquema de logs, SLOs, alertas G10, limitaciones y decisiones 1–9.
- [x] Gates en verde y commit `docs: activate spec 007 observability`.

## B1 — Núcleo de métricas

- [ ] `application/metrics_port.py`: enums cerrados, `MetricsRecorder`, snapshot inmutable.
- [ ] `infrastructure/metrics.py`: `MetricsRegistry` con lock, reloj inyectable,
      contadores e histograma con p50/p95 aproximados.
- [ ] `tests/test_metrics_registry.py`: incrementos, etiquetas inválidas, histograma,
      percentiles, concurrencia, snapshot y JSON.
- [ ] Verificar `test_import_boundaries.py`.

## B2 — Instrumentación HTTP

- [ ] Medir peticiones, status y latencia por endpoint normalizado.

## B3 — Instrumentación de aplicación y correlación

- [ ] Medir llamadas al proveedor, tokens, `generated`, `fallback_reason` y moderación.
- [ ] Inyectar `request_id` en logs por filtro, sin enviarlo a Gemini.

## B4 — Presupuesto diario

- [ ] `Settings` con clave de métricas, tarifas, límite de llamadas y límites de tokens.
- [ ] `DailyBudget` con UTC-6 fijo, consumo controlado y `BUDGET_EXHAUSTED`.
- [ ] Coste estimado con `Decimal`; sin dependencias nuevas.

## B5 — Endpoints internos

- [ ] `GET /internal/metrics` y `GET /internal/health/detail` con `GENAI_METRICS_KEY`.
- [ ] Sin `provider_model`, sin contenido, sin stack traces.

## B6 — No-fuga

- [ ] Pruebas de ausencia de contenido, credenciales y PII en logs y métricas.

## B7 — Pruebas y cierre

- [ ] Validar dashboards/alertas solo como documentación para G10.
- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a `IMPLEMENTED` solo al cumplir todo.
