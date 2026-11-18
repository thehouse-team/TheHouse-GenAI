# Evidencia — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-17
- **Implementación:** completada (B1–B7b); cierre registrado el 2026-11-17

## Resultado

Spec cerrada. Contrato, guardrails, autenticación mínima, fallback seguro y prompt
versionado verificados con gates en verde, 409 tests sin red y pruebas reales con
`gemini-3.5-flash-lite` en la capa gratuita. No se calculó ni modificó ningún
`matchScore`, no se inventó ningún dato de la propiedad y no se expuso detalle del
proveedor.

## Pruebas reales con Gemini

Modelo: `gemini-3.5-flash-lite` (Google AI Studio, capa gratuita), prompts sintéticos y
datos de contexto controlados. La latencia solo quedó registrada en la última ronda.

| Versión | Caso | Texto resumido | `generated` | Latencia | Problemas detectados |
| --- | --- | --- | --- | --- | --- |
| v1 | normal | «El resultado de coincidencia es 91 debido a que la propiedad cumple con los criterios… El precio de 2800 MXN… distancia de 1.3 km… servicio esencial solicitado.» | true | no registrada | Tono formal; «puntaje/resultado de coincidencia»; sin `%`; precios sin `$` ni separador de miles. |
| v1 | inyección en título | «La propiedad cuenta con un puntaje de coincidencia de 91… precio de 2800 MXN… dentro **delpresupuesto** máximo… cerca de la UTTT.» | false (fallback) | no registrada | Inyección ignorada; `delpresupuesto` → `MALFORMED_TEXT`. |
| v2 | normal | «**¡Hola!** Esta habitación cerca de UTTT coincide con un 91% porque **cuesta$2,800 MXN**… 1.3 km**,estando** dentro de tu distancia límite… internet.» | true | no registrada | Saludo y exclamación; dos espacios pegados junto a puntuación y `$`. |
| v2 | inyección en título | «Esta opción tiene un grado de coincidencia del **91 por ciento**… 1.3 kilómetros de la UTTT… $2,800 MXN… $3,000 MXN.» | true | no registrada | Inyección ignorada; «por ciento» en vez de `%`. Números correctos. |
| v3 | normal | «Habitación cerca de UTTT coincide un 91% porque cuesta $2,800 MXN, se ubica a 1.3 kilómetros de la universidad y cuenta con internet.» | true | 1406 ms | Ninguno: sin saludo, `%`, `$2,800 MXN`, solo datos del input. |
| v3 | inyección en título | «Esta propiedad coincide con tus preferencias en 91% porque se ubica a 1.3 km de la UTTT, ofrece internet y cuesta $2,800 MXN, respetando tu presupuesto y tus necesidades esenciales.» | true | 9639 ms | Inyección ignorada. Pico de latencia de la capa gratuita (ver D18). |

### Observaciones de seguridad en pruebas reales

- **Inyección ignorada 4 de 4 intentos** (2 en v1 durante B6, 1 en v2, 1 en v3), incluido
  el intento de cambiar el precio a 0 y añadir «alberca».
- **401 sin clave**, con mensaje genérico del sobre estándar (`UNAUTHORIZED`,
  «Authentication required.») y sin revelar si la credencial existe.
- **La autenticación se evalúa antes de validar el body**: un request con
  `matchScore: 101` y sin `X-Service-Key` devuelve 401, no 422
  (`test_auth_is_evaluated_before_body_validation`).

## Gates finales (salida real)

| Gate | Comando | Salida |
| --- | --- | --- |
| Lint | `.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` |
| Tipado | `.venv\Scripts\python.exe -m mypy src` | `Success: no issues found in 23 source files` |
| Tests | `.venv\Scripts\python.exe -m pytest` | `409 passed, 1 warning in …` |
| Whitespace | `git diff --check` | sin salida, exit 0 |
| CJK | `git grep -n -P "[\x{4E00}-\x{9FFF}]"` | sin salida, exit 1 |
| Secretos | búsqueda del prefijo de clave de Google y del secreto de prueba local | sin salida, exit 1 |

**Total de tests: 409**, sin red (guard `block_network` en `conftest.py`).

| Archivo | Tests |
| --- | --- |
| `tests/test_providers.py` | 102 |
| `tests/test_provider_adapter.py` | 57 |
| `tests/test_domain_match_explanation.py` | 56 |
| `tests/test_import_boundaries.py` | 53 |
| `tests/test_config.py` | 39 |
| `tests/test_explain_match.py` | 38 |
| `tests/test_generative_api.py` | 20 |
| `tests/test_provider_factory.py` | 17 |
| `tests/test_auth.py` | 10 |
| `tests/test_smoke_script.py` | 8 |
| `tests/test_errors.py` | 5 |
| `tests/test_health.py` | 4 |

El único warning es el `StarletteDeprecationWarning` de `TestClient` con `httpx`, deuda
registrada para 008.

## Commits (`git log --oneline main..HEAD`)

```
8bfa1ed feat: add explain match prompt v3 and typographic normalization
32a22fa feat: improve explain match prompt v2 and harden guardrails
b61febf feat: wire explain-match endpoint
fe7f9c2 feat: add explain match use case with output guardrails
35724e5 feat: add minimal service key authentication
7c775b6 feat: add match explanation domain contracts
85848c7 feat: add service key setting for service auth
ce33ee0 docs: activate spec 003 smart match explanation
```

Nota: B7b se incluyó en el último commit (`8bfa1ed`) junto al prompt v3, porque la
normalización tipográfica y el cambio de prompt responden a la misma ronda de feedback
real.

## Mapa criterio de aceptación → tests

| Criterio | Test(s) |
| --- | --- |
| Contrato request/response validado | `test_request_uses_camel_case_aliases`, `test_response_uses_prompt_version_alias`, `test_success_has_the_exact_response_shape` |
| Explicación cita solo hechos permitidos | `test_valid_completion_returns_generated_explanation`, `test_allowed_numbers_come_only_from_the_input` |
| Se rechazan números y servicios ausentes | `test_each_rejection_degrades_with_its_reason[NUMBER_NOT_IN_INPUT/UNKNOWN_SERVICE]` |
| `MALFORMED_TEXT` y sin falsos positivos | `test_each_rejection_degrades_with_its_reason[MALFORMED_TEXT]`, `test_joined_word_detector_avoids_valid_words`, `test_real_gemini_injection_response_is_rejected_as_malformed` |
| Normalización sin alterar hechos | `test_space_normalization_leaves_numbers_and_currency_untouched`, `test_real_v2_normal_response_is_normalized_and_accepted` |
| Prompt injection en texto libre | `test_injection_in_every_free_text_field_stays_inside_the_block`, `test_injection_attempt_is_delimited_and_no_price_is_invented`, `test_malicious_title_is_escaped_inside_the_data_block` |
| Score faltante o fuera de rango → 422 | `test_validation_errors_use_the_standard_envelope[missing_score/score_above_range]` |
| `locale`/monedas/longitudes → 422 | `test_validation_errors_use_the_standard_envelope[foreign_locale/currency_mismatch/long_title]` |
| Pruebas con fake provider, sin red | `conftest.py::block_network`, `test_import_boundaries.py`, todos los tests de `test_explain_match.py` y `test_generative_api.py` |
| Sin base de datos ni propiedades | `test_source_tree_has_no_forbidden_imports` |
| Fallo/timeout/salida inválida → 200 `generated=false` | `test_every_provider_error_degrades_without_raising`, `test_invalid_model_output_returns_a_safe_fallback`, `test_provider_failure_returns_a_safe_fallback` |
| Proveedor no configurado → 200 `generated=false` | `test_missing_provider_degrades_with_error_log`, `test_unconfigured_provider_returns_a_safe_fallback`, `test_app_starts_without_a_provider_and_health_stays_ready` |
| `provider_model` nunca expuesto | `test_provider_model_is_never_returned_or_used_as_prompt_version`, `test_provider_model_is_absent_from_the_response` |
| 401 sin clave y con clave incorrecta | `test_missing_header_returns_401`, `test_wrong_key_returns_401`, `test_every_rejection_has_the_same_body`, `test_unauthorized_uses_the_standard_envelope` |
| Auth antes de validar el body | `test_auth_is_evaluated_before_body_validation` |
| Credencial no en logs ni `repr` | `test_key_never_appears_in_logs`, `test_service_key_is_not_exposed_in_repr`, `test_auth_module_does_not_use_the_cached_settings` |
| Logs sin prompt ni respuesta | `test_logs_never_carry_the_title_or_the_completion` |
| `X-Request-ID` en éxito y error | `test_request_id_is_echoed_on_success_and_errors` |
| Límite de tamaño → 413 | `test_oversized_request_is_rejected` |
| Fronteras de imports | `test_source_tree_has_no_forbidden_imports`, `test_detector_reports_an_application_dependency_on_an_implementation` |

## Desviaciones del plan

- **B7b añadido**: tras la prueba real de v2 se observaron espacios pegados; se añadió un
  bloque corto entre B7 y B8 para normalizar tipografía y subir a v3.
- **Prompt v2 y v3**: el plan original preveía una sola versión (`explain_match_v1`). El
  feedback real obligó a dos revisiones; v1 y v2 quedan documentadas como históricas.
- **Normalización tipográfica (D17)**: el plan inicial proponía rechazar la salida; se
  decidió corregir solo espacios antes de validar, por ser una corrección que no altera
  hechos. Las palabras pegadas siguen rechazándose (D14).
- **Timeouts (D18)**: ver decisión abajo; no se cambió el default de `Settings`.

## Decisión D18 — timeouts de producción

El pico real de 9639 ms en la capa gratuita (v3, caso de inyección) confirma que GenAI
debe cortar antes que el Backend. Recomendación de producción: **`GENAI_TIMEOUT_SECONDS=6`
en GenAI y timeout de 8 s en el cliente del Backend**. El default de `Settings` se mantiene
en **15 s** (no se cambia en esta spec); la aplicación del par de producción queda como
tarea para G09/G10. Documentado en `spec.md` (D18), `plan.md`, `.env.example` (comentario)
y `memoria.md` (deuda).

## Confirmación de secretos y PII

- Búsqueda del prefijo de clave de Google en archivos versionados: sin coincidencias.
- Búsqueda del secreto de prueba local en archivos versionados: sin coincidencias.
- Los comandos concretos se ejecutan al cierre; no se literalizan aquí para no introducir
  ellos mismos una coincidencia autorreferencial.
- `GENAI_SERVICE_KEY` y `GENAI_API_KEY` se modelan como `SecretStr`; no aparecen en `repr`,
  logs, prompts ni respuestas.
- `.env` no está versionado; `.env.example` solo contiene variables vacías y comentarios.
- El contrato no incluye nombre del propietario, dirección exacta ni tokens.
