# Evidencia — 007-observability Observabilidad

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-18
- **Implementación:** completada (B0–B7) sobre la rama `feature/observability`

## Resultado

Spec cerrada. Métricas en memoria con etiquetas cerradas e histograma de latencia,
presupuesto diario configurable con coste `Decimal`, endpoints internos protegidos con
clave separada, correlación de logs por `request_id` y SLOs/alertas documentados para G10.
Sin dependencias nuevas, sin red en la suite y sin cambios en los contratos de health ni
de `explain-match`.

## Gates finales (salida real)

| Gate | Comando | Salida |
| --- | --- | --- |
| Lint | `.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` |
| Tipado | `.venv\Scripts\python.exe -m mypy src` | `Success: no issues found in 32 source files` |
| Tests | `.venv\Scripts\python.exe -m pytest` | `775 passed, 1 warning in 4.07s` |
| Whitespace | `git diff --check` | sin salida, exit 0 |
| CJK/fullwidth | `git grep -n -P "[\x{4E00}-...]"` | sin salida, exit 1 |
| Credencial Google | búsqueda del prefijo de clave de Google | sin salida, exit 1 |
| Clave local 005 | búsqueda del secreto de prueba de 005 | sin salida, exit 1 |
| Clave local 007 | búsqueda del secreto de prueba de 007 | sin salida, exit 1 |

El único warning es el `StarletteDeprecationWarning` heredado de `TestClient` con `httpx`
(deuda (e)/006-(d), registrada para 008). Sin red: guard `block_network` activo.

**Total de tests: 775**, sin red.

| Archivo | Tests |
| --- | --- |
| `tests/test_providers.py` | 102 |
| `tests/test_moderation_provider.py` | 67 |
| `tests/test_moderation_policy.py` | 66 |
| `tests/test_prompt_injection_corpus.py` | 65 |
| `tests/test_domain_match_explanation.py` | 56 |
| `tests/test_import_boundaries.py` | 55 |
| `tests/test_config.py` | 51 |
| `tests/test_provider_adapter.py` | 57 |
| `tests/test_explain_match.py` | 38 |
| `tests/test_metrics_registry.py` | 26 |
| `tests/test_generative_api.py` | 21 |
| `tests/test_internal_endpoints.py` | 16 |
| `tests/test_budget.py` | 12 |
| `tests/test_http_metrics.py` | 13 |
| `tests/test_security_headers.py` | 12 |
| `tests/test_rate_limit.py` | 11 |
| `tests/test_auth.py` | 10 |
| `tests/test_key_rotation.py` | 8 |
| `tests/test_smoke_script.py` | 8 |
| `tests/test_security_logging.py` | 7 |
| `tests/test_gemini_safety.py` | 6 |
| `tests/test_ci_security.py` | 6 |
| `tests/test_errors.py` | 5 |
| `tests/test_pii_allowlist.py` | 5 |
| `tests/test_health.py` | 4 |
| `tests/test_observability_leak_checks.py` | 4 |
| `tests/test_moderation_output.py` | 13 |
| `tests/test_provider_factory.py` | 17 |
| `tests/test_observability.py` | 14 |

## Commits (`git log --oneline main..HEAD`)

```
a4be59b test: add observability leak and cardinality checks
182eeff feat: add protected internal metrics and health detail endpoints
dd3efe5 feat: add daily provider budget with cost estimate
3975793 feat: instrument explain-match metrics and correlate request ids
2f10fc2 feat: add http request metrics
d04ed35 feat: add in-memory metrics registry
52b4e91 docs: activate spec 007 observability
```

## Mapa criterio de aceptación → tests

| Criterio | Tests / evidencia |
| --- | --- |
| Schema de logs documentado y probado | Apéndice A de `spec.md`; `test_json_formatter_emits_only_allowlisted_extra_fields`, `test_json_logging_emits_the_provider_metadata` |
| Métricas internas con nombres estables | `test_metrics_registry.py` (26), `test_http_metrics.py` (13), `test_internal_endpoints.py::test_metrics_snapshot_reflects_real_requests` |
| Correlación de una request por `request_id` | `test_observability.py::test_request_id_is_correlated_without_reaching_gemini`, `::test_request_id_filter_keeps_explicit_and_neutral_values` |
| SLOs y alertas aprobados y documentados | Apéndice B de `spec.md` (documentación para G10; sin implementación) |
| Ausencia de contenido sensible | `test_observability_leak_checks.py` (4), `test_security_logging.py` (7), `test_pii_allowlist.py` (5) |
| Coste y tokens sin almacenar texto | `test_budget.py::test_cost_is_exact_decimal_and_exposed_as_a_string_gauge`, `test_observability.py::test_success_records_provider_tokens_and_outcome` |
| Presupuesto: fallback sin llamar al proveedor | `test_budget.py::test_exhausted_budget_returns_a_fallback_without_calling_gemini`, `::test_token_limit_blocks_the_following_call`, `::test_failed_call_consumes_a_slot_but_no_tokens`, `::test_midnight_rollover_resets_counters_with_a_fake_clock`, `::test_concurrent_reservations_never_exceed_the_limit` |
| Endpoints internos protegidos | `test_internal_endpoints.py` (16); `test_cors_allows_the_metrics_key_header` |
| Contrato de health intacto | `test_health.py` (4), `test_internal_endpoints.py::test_g01_health_probes_keep_their_exact_payload` |
| Contrato de `explain-match` intacto | `test_http_metrics.py::test_explain_match_contract_is_unchanged`, `test_generative_api.py::test_success_has_the_exact_response_shape` |
| Cardinalidad acotada y etiquetas cerradas | `test_observability_leak_checks.py::test_unknown_and_id_paths_are_grouped_as_other`, `::test_every_snapshot_label_belongs_to_a_closed_enum` |
| Fronteras de imports y sin dependencias nuevas | `test_import_boundaries.py` (55), incluyendo `::test_application_never_imports_infrastructure` y `::test_domain_never_imports_providers_api_or_infrastructure`; `pyproject.toml` sin cambios |

## Fallos intermedios reportados y corrección

| Bloque | Fallo | Corrección |
| --- | --- | --- |
| B1 | `test_snapshot_is_frozen_and_independent`: esperaba 2 contadores, pero el mismo conjunto de etiquetas acumula en uno con valor 2 | Ajustada la aserción a 1 contador con valor 2 |
| B1 | Ruff `RUF022` (`__all__` sin ordenar) y `S105` (variable `secret_marker`) | Ordenado `__all__`; variable renombrada a `rejected_value` |
| B2 | Ruff `E501` en `test_http_metrics.py` | Partida la línea en dos |
| B3 | `test_request_id_is_correlated_without_reaching_gemini`: el `MockTransport` devolvía texto plano y el caso de uso degradaba con `INVALID_JSON` | El fixture devuelve `_completion()` (JSON) |
| B4 | `test_disabled_budget_never_blocks_or_reports_exhaustion` (dos fallos seguidos): `calls_used==0` con presupuesto apagado y `DailyBudgetPort` no era `@runtime_checkable` | `reserve_call` cuenta el uso sin bloquear cuando está apagado; puerto marcado `@runtime_checkable` |
| B4 | Ruff `RUF022`, `SIM103` e `I001` | Orden de `__all__` e imports; condición final devuelta directamente |
| B5 | `test_metrics_snapshot_reflects_real_requests`: `_count` filtraba con etiquetas vacías y no sumaba todos los `http_requests_total` | Helper `_count` suma todos los contadores del nombre cuando no hay etiquetas |

B6 no tuvo fallos intermedios.

## Desviaciones del plan

1. **Sin `infrastructure/tracing.py`**: la correlación se logra con un `logging.Filter` que
   inyecta el `request_id` del `ContextVar`; no hay `trace_id`, spans ni librería de trazas.
2. **UTC-6 fijo**: sin `tzdata`; CDMX no observa horario de verano desde 2022. Documentado
   el desfase con el reinicio de cuota de Gemini a medianoche hora del Pacífico.
3. **Presupuesto que cuenta uso aunque esté apagado**: `reserve_call` incrementa el
   contador de llamadas pero nunca bloquea cuando `budget_enabled=False`, para que el
   detalle interno refleje el uso real.
4. **Contador separado `metrics_auth_rejections_total`**: los rechazos de `X-Metrics-Key`
   no se mezclan con los de `X-Service-Key`.
5. Extensiones menores del puerto de métricas: parámetro `amount` en `increment` para los
   tokens reportados y campo `gauges` en el snapshot para el coste `Decimal` como string.

## Prueba manual real (2026-11-18)

Servidor local con Gemini real, ejecutada por el usuario. No se usó red en la suite
automática: esta sección registra únicamente la prueba manual proporcionada.

| Comprobación | Resultado |
| --- | --- |
| `explain-match` con `X-Service-Key` | `200` |
| `explain-match` sin clave | `401` |
| `/internal/metrics` con la clave de métricas | `200` |
| `/internal/metrics` con la clave de servicio | `401` |
| `/internal/health/detail` con la clave de métricas | `200` |

Contadores observados en `/internal/metrics`: `auth_rejections_total{missing_key}=1`,
`explain_match_outcomes_total{generated=true}=1`, `http_requests_total` con `200=1` y
`401=1`, `moderation_decisions_total{allow}=1`, `provider_calls_total{success}=1`,
`provider_tokens_total` con entrada `421` y salida `44`, y
`provider_estimated_cost="0"` (capa gratuita). El snapshot no contenía textos, claves,
`request_id` ni modelo del proveedor.

`/internal/health/detail` devolvió `status=ok`, `provider.configured=true`,
`moderator.configured=true`, `budget.enabled=false` y
`resets_at=2026-11-19T00:00:00-06:00`.

### Hallazgo y corrección

El histograma `http_request_duration_ms` mezclaba el `200` de `explain-match` (~1,3 s) con
el `401` (casi instantáneo), de modo que `p50_ms_approx` salió en **50 ms** y el SLO de
latencia quedaba distorsionado por respuestas rápidas de error.

Corrección aplicada:

1. La etiqueta cerrada `status_class` (`2xx`, `4xx`, `5xx`, `other`) separa las series
   del histograma; un `200` y un `401` ya no comparten serie.
2. El SLO de latencia de `spec.md` se mide **solo** sobre `status_class=2xx`.
3. Tests: `test_success_and_401_latencies_are_separate_series`,
   `test_histogram_labels_include_the_closed_status_class` y la comprobación de
   cardinalidad en `test_unknown_and_id_paths_are_grouped_as_other`.

## Confirmación de secretos y PII

- Búsquedas del prefijo de credencial de Google y de los secretos de prueba de 005 y 007:
  sin coincidencias. Los patrones concretos no se literalizan aquí para no introducir una
  coincidencia autorreferencial.
- `GENAI_SERVICE_KEY`, `GENAI_SERVICE_KEY_PREVIOUS`, `GENAI_METRICS_KEY` y `GENAI_API_KEY`
  se modelan como `SecretStr`; no aparecen en `repr`, logs, métricas ni respuestas.
- Las etiquetas del snapshot salen solo de enums cerrados: sin prompts, respuestas,
  títulos, `request_id`, fingerprints ni ids de modelo.
- `.env` no está versionado; `.env.example` contiene solo variables vacías/comentadas.
