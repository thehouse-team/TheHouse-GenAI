# Evidencia — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-18
- **Rama:** `feature/natural-language-search`
- **Cierre:** B0–B7 completados; contract tests e integración quedan para G09/G10 (008/010).

## Gates (salida real)

```
.venv\Scripts\python.exe -m ruff check .
All checks passed!

.venv\Scripts\python.exe -m mypy src
Success: no issues found in 36 source files

.venv\Scripts\python.exe -m mypy --strict scripts/smoke_parse_search.py
Success: no issues found in 1 source file

.venv\Scripts\python.exe -m pytest
1021 passed, 1 warning in 7.95s
```

El único warning es el `StarletteDeprecationWarning` heredado de `TestClient` con `httpx`
(deuda (e)/008). La suite corre sin red: el fixture `block_network` de `tests/conftest.py`
es `autouse` y los dos scripts manuales solo se ejecutan de forma explícita y opt-in.

```
git diff --check
(sin salida, exit 0)

git grep -n -P "[\x{4E00}-\x{9FFF}\x{3000}-\x{303F}\x{FF00}-\x{FFEF}]"
(sin salida, exit 1 = sin coincidencias)

```

Las tres búsquedas adicionales de secretos (patrón de credencial de API, clave local de
prueba de servicio y clave local de prueba de métricas) devolvieron sin coincidencias,
`exit 1` en los tres casos. No hay secretos, credenciales, claves de métricas ni PII real
versionada. El corpus usa
solo datos sintéticos y términos de moderación ficticios; el léxico de moderación nunca
se abrió ni se citó en los tests de esta spec.

## Commits (`git log --oneline main..HEAD`)

```
e4ebfcc fix: prune invalid services in parse-search output and add smoke diagnostics
cd76e62 test: add search query corpus and manual parse-search smoke script
703cfca feat: add parse-search endpoint
ed046ae test: cover parse-search moderation and pii end to end
17800cf feat: add parse-search use case with pii redaction and fallbacks
b99dc83 feat: add parse-search guardrails and deterministic confidence
a4604f6 feat: add search filter domain and deterministic extractors
0b96f72 docs: activate spec 004 natural language search
```

## Mapa criterio → tests

| Criterio (spec/RF) | Tests |
| --- | --- |
| Contrato exacto, aliases camelCase, `extra="forbid"`, `promptVersion` | `tests/test_parse_search.py::test_happy_path_returns_the_exact_contract`, `tests/test_domain_search_filters.py`, `tests/test_parse_search_api.py::test_success_has_the_exact_alias_shape` |
| `maxBudget`/`maxDistanceKm` como números JSON | `tests/test_parse_search_api.py::test_success_has_the_exact_alias_shape`, `::test_decimal_distance_is_a_json_number`, `::test_null_numeric_filters_stay_null` |
| Distancia: `3 km` vs `3k`, minutos sin convertir | `tests/test_domain_search_filters.py`, `tests/test_search_query_corpus.py` (ps-07, ps-08, ps-09, ps-10, ps-17, ps-30) |
| Universidad con evidencia o alias canónico | `tests/test_parse_search_guardrails.py`, corpus ps-03/ps-07/ps-29 |
| Rango "entre 2000 y 3000" → 3000 y `medium` | `tests/test_parse_search_guardrails.py`, corpus ps-11 |
| Poda por evidencia, normalización y dedup de servicios | `tests/test_parse_search_guardrails.py`, `tests/test_parse_search.py::test_model_services_are_normalized_and_only_invalid_are_pruned`, `tests/test_search_query_corpus.py::test_ps_03_misspelled_service_is_pruned_not_rejected`, `::test_ps_20_corpus_is_grounded_and_the_guardrail_does_not_invent_services` |
| Confianza determinista; `confidence` nunca del modelo | `tests/test_parse_search_guardrails.py`, `tests/test_parse_search.py::test_confidence_is_never_taken_from_the_model` |
| Fallos de proveedor, timeout, JSON inválido, presupuesto → 200 vacío | `tests/test_parse_search.py`, `tests/test_parse_search_api.py::test_provider_failure_returns_a_safe_fallback`, `::test_exhausted_budget_returns_a_safe_fallback`, `::test_raw_completion_rejects_extra_fields_and_wrong_types` |
| PII redactada antes del prompt y de los logs | `tests/test_parse_search_pii.py`, `tests/test_pii_allowlist.py` |
| Moderación de entrada/salida y error del moderador | `tests/test_parse_search_moderation.py`, `tests/test_moderation_output.py` |
| Inyección escapada y registrada, nunca rechazada | `tests/test_search_text_guard.py`, `tests/test_prompt_injection_corpus.py`, `tests/test_parse_search.py::test_injection_is_escaped_and_logged_without_rejection`, `tests/test_smoke_parse_search.py::test_injection_detection_line_is_silent_in_the_console` |
| HTTP: 401/422/429, headers, `X-Request-ID`, ruta de métricas | `tests/test_parse_search_api.py`, `tests/test_http_metrics.py`, `tests/test_security_headers.py` |
| Corpus versionado y script manual protegido | `tests/test_search_query_corpus.py`, `tests/test_smoke_parse_search.py`, `tests/test_import_boundaries.py` |

## Pruebas reales con Gemini (`gemini-3.5-flash-lite`, capa gratuita)

Todas las corridas usaron `scripts/smoke_parse_search.py`, `delay=8 s`, consultas
sintéticas y `--i-have-a-real-key`; la credencial nunca se imprimió (solo su longitud).

1. **Primera corrida (5 casos).** Tres exactos (ps-01, ps-02, ps-05); ps-04 terminó en
   `PROVIDER_UNAVAILABLE` y ps-03 en `INVALID_JSON`. La salida mostraba aún las líneas
   crudas `provider.call.failed` y `parse_search.fallback`.
2. **Diagnóstico de ps-03.** Con `--only ps-03 --diagnose`, el script mostró estructura
   correcta (claves y tipos esperados, sin extras ni envoltura) y
   `filters.essentialServices: value_error`. Eso reveló que la completion se validaba con
   el modelo de dominio estricto (vocabulario cerrado y sin duplicados), de modo que una
   etiqueta de servicio inválida descartaba toda la respuesta, en contra de D2/B2.
   Corrección: modelo `RawParseSearchCompletion` para la propuesta del modelo y
   normalización/poda en guardrails; el modelo estricto valida solo la salida final.
   `PROVIDER_UNAVAILABLE` se mantuvo como degradeo 200 con `low` (no se relajó la
   validación).
3. **Corrida completa (30 casos).** 27/30 exactos. Por campo: `maxBudget` 29/30,
   `currency` 29/30, `maxDistanceKm` 30/30, `university` 28/30, `essentialServices`
   28/30, `petsAllowed` 29/30. Latencia min 826 ms, mediana 1254 ms, max 1824 ms.
   `ALL_FILTERS_PRUNED` en ps-08, ps-13 y ps-24 (vagos, esperado). ps-10 y ps-29 fallaron
   por `PROVIDER_UNAVAILABLE` de Gemini; ps-03 reconoció UNAM.
4. **Reintentos.** ps-10: exacto (maxBudget 3000, MXN, UTTT, `high`, `generated=true`,
   1631 ms). ps-29: exacto (UNAM, `estacionamiento`, `petsAllowed=true`, `high`,
   `generated=true`, 2596 ms). Sin errores en ninguno.
5. **Consolidado:** 29/30 exactos. Los dos `PROVIDER_UNAVAILABLE` salieron exactos al
   reintentar. Único desajuste real: ps-20.

### Análisis de ps-20

La query del corpus es `Cuarto amueblado con wifi y agua` y su `expectedFilters` pide
`["agua", "amueblado", "internet"]`. La query **sí** menciona `wifi` (sinónimo determinista
de `internet`) y `amueblado`, y `extract_services(query)` devuelve exactamente esos tres
servicios. El modelo devolvió `["agua", "internet"]`: omitió `amueblado`. No era un error
del corpus ni una poda indebida del guardrail (los guardrails no inventan filtros por D9).
No se cambió el corpus ni el guardrail; se añadió
`test_ps_20_corpus_is_grounded_and_the_guardrail_does_not_invent_services`, que verifica
la evidencia de la query y que una completion sin `amueblado` no lo inventa.

## Corrección del contrato numérico

El ejemplo de la spec muestra `maxBudget: 3000` como número, pero Pydantic v2 serializa
`Decimal` como string en modo JSON. Backend usa `System.Text.Json`, que no acepta
`"3000"` en un `decimal` sin configuración especial. Se añadió un
`field_serializer(when_used="json")` en `SearchFilters` que emite `int` para valores
enteros y `float` para valores con decimales, manteniendo `Decimal` internamente. La spec
y la guía compartida quedaron actualizadas; los tests del API defienden el tipo en
`response.json()`. Las métricas internas (`provider_estimated_cost` como string) no se
cambiaron, según lo decidido en 007.

## Fallos intermedios reportados y corregidos

- B4: `maxBudget` serializado como string y `caplog` desconectado al crear la app; se
  corrigió la serialización en producción y se sustituyó `caplog` por un handler directo.
- B5: `caplog` desconectado por `create_app` al probar los logs del caso de uso; se
  sustituyó por un handler directo sobre `thehouse_genai.application.parse_search`.
- B6: `mypy` sobre el tuple de handlers, `ROOT` como `str` en el wrapper y registro del
  módulo en `sys.modules` para los tests del script; corregidos.
- Diagnósticos: el filtro de consola no ocultaba `parse_search.fallback` ni
  `parse_search.injection_detected`; ampliado sin tocar el logging del servicio.
- Parser: `strict=True` de Pydantic rechazaba números JSON para `Decimal` y el validador
  `before` era necesario para rechazar strings; se ajustó por campo.
- Correcciones de tipos: `apply_guardrails` acepta `SearchFilters | RawSearchFilters` y
  el script de diagnóstico re-valida con el modelo crudo.

Todos los fallos se reportaron al usuario cuando ocurrieron y los gates quedaron en verde
antes de cada commit. La evidencia de cada bloque está en los commits listados arriba.
