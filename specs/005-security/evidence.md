# Evidencia — 005-security Seguridad de servicio e IA

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-17
- **Implementación:** completada (B0–B8)

## Resultado

Spec cerrada. G05 endurece la autenticación mínima de 003 sin rehacerla: rotación de la
clave de servicio, rate limiting por cliente en memoria, allowlist explícita de campos
del prompt, corpus versionado de prompt injection con normalización de homoglifos,
headers de seguridad, logging de 401/429 y auditoría de dependencias en CI. El contrato
HTTP de `explain-match` no cambió: misma request y misma response; el único código nuevo
es `429` con `Retry-After`.

No se calculó ni modificó ningún `matchScore`, no se inventó ningún dato de la
propiedad, no se expuso detalle del proveedor y no se registraron credenciales, bodies
ni PII en logs.

## Gates finales (salida real)

| Gate | Comando | Salida |
| --- | --- | --- |
| Lint | `.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` |
| Tipado | `.venv\Scripts\python.exe -m mypy src` | `Success: no issues found in 25 source files` |
| Tests | `.venv\Scripts\python.exe -m pytest` | `536 passed, 1 warning in 2.86s` |
| Whitespace | `git diff --check` | sin salida, exit 0 |
| CJK | `git grep -n -P "[\x{4E00}-\x{9FFF}]"` | sin salida, exit 1 |
| Secretos | búsqueda del prefijo de clave de Google y del secreto de prueba local | sin salida, exit 1 |

**Total de tests: 536**, sin red (guard `block_network` en `conftest.py`), con un único
warning heredado de `TestClient` con `httpx` (deuda de 008).

| Archivo | Tests |
| --- | --- |
| `tests/test_providers.py` | 102 |
| `tests/test_provider_adapter.py` | 57 |
| `tests/test_domain_match_explanation.py` | 56 |
| `tests/test_import_boundaries.py` | 53 |
| `tests/test_config.py` | 49 |
| `tests/test_explain_match.py` | 38 |
| `tests/test_prompt_injection_corpus.py` | 37 |
| `tests/test_generative_api.py` | 21 |
| `tests/test_provider_factory.py` | 17 |
| `tests/test_security_headers.py` | 12 |
| `tests/test_key_rotation.py` | 8 |
| `tests/test_auth.py` | 10 |
| `tests/test_smoke_script.py` | 8 |
| `tests/test_pii_allowlist.py` | 6 |
| `tests/test_rate_limit.py` | 13 |
| `tests/test_security_logging.py` | 7 |
| `tests/test_ci_security.py` | 6 |
| `tests/test_errors.py` | 5 |
| `tests/test_health.py` | 4 |

## Commits (`git log --oneline main..HEAD`)

```
f17edf8 ci: add non-blocking dependency audit
6d56380 feat: add security event logging
a1be596 feat: add security response headers
c2612fc feat: add in-memory rate limiting with retry-after
5957058 test: add versioned prompt injection corpus and homoglyph detection
24db9f3 feat: add prompt field allowlist for pii minimization
b5e4625 feat: support service key rotation
26d3f64 docs: activate spec 005 security
```

## Prueba manual real (2026-11-17)

Servidor local con `GENAI_RATE_LIMIT_REQUESTS=2`, `GENAI_PROVIDER=gemini` y Gemini real.
Tres peticiones válidas consecutivas al endpoint de `explain-match`:

| Petición | Resultado | Proveedor |
| --- | --- | --- |
| 1 | `200`, explicación generada | llamado |
| 2 | `200`, explicación generada | llamado |
| 3 | `429 TOO_MANY_REQUESTS` con `Retry-After` | **no llamado** |

Las tres respuestas, y también los errores `400`, incluyeron los cuatro headers de
seguridad: `cache-control: no-store`, `x-content-type-options: nosniff`,
`referrer-policy: no-referrer` y `x-frame-options: DENY`.

### Comportamiento conocido: body inválido antes que la autenticación

Un primer intento con JSON mal codificado (acento enviado sin UTF-8 desde la terminal)
devolvió `400 BAD_REQUEST` antes de evaluar la autenticación. Con `TestClient`, un body
que no es JSON válido y sin `X-Service-Key` devuelve `422 VALIDATION_ERROR`
(`tests/test_generative_api.py::test_invalid_json_without_key_is_rejected_before_authentication`).
En ambos casos el error de parseo se evalúa antes que el guard de autenticación. El
mensaje es genérico (`Request validation failed.` / `Bad request.`) y no expone el body,
el acento ni ningún dato de la request. No se cambió el orden de procesamiento: queda
registrado como deuda en `memoria.md`.

## Configuración de GitHub (D8)

Activada en GitHub Settings el 2026-11-17; la evidencia son capturas guardadas fuera del
repositorio, no se versionan secretos ni configuraciones de cuenta:

- Secret scanning y push protection.
- Dependabot: dependency alerts, malware alerts y security updates.
- CodeQL default setup.

`pip-audit` se ejecuta en CI con `continue-on-error: true`, instalado solo en el job;
no se usa gitleaks y `pyproject.toml` no se modificó. Los gates bloqueantes siguen siendo
ruff, mypy y pytest (`tests/test_ci_security.py`).

## Mapa criterio de aceptación → tests

| Criterio | Test(s) / evidencia |
| --- | --- |
| Threat model y data flow documentados | `spec.md`, apéndice y sección «Rate limiting y operación» |
| 401 con sobre estándar | `test_unauthorized_uses_the_standard_envelope`, `test_every_rejection_has_the_same_body`, `test_each_401_reason_is_logged` |
| Rotación, fail closed y comparación contra todas | `test_current_key_is_accepted_during_rotation`, `test_previous_key_is_accepted_during_rotation`, `test_only_previous_key_fails_closed`, `test_every_configured_key_is_compared_even_when_the_current_one_matches`, `test_generic_service_key_previous_env_is_ignored` |
| Tokens de usuario rechazados/no reenviados | `test_access_token_payload_is_rejected_without_reaching_logs` |
| Allowlist del prompt y regresión del schema | `test_prompt_field_allowlist_matches_the_request_schema`, `test_to_context_emits_only_allowlisted_keys`, `test_allowlist_excludes_sensitive_fields` |
| Corpus versionado y homoglifos | `tests/test_prompt_injection_corpus.py` (completo), `test_homoglyph_and_zero_width_markers_are_detected`, `test_detection_normalization_leaves_the_returned_text_untouched` |
| 429 con sobre estándar y `Retry-After` | `test_exceeding_the_limit_returns_429_with_retry_after`, `test_window_resets_with_the_fake_clock`, prueba manual |
| Límite por proceso documentado | `spec.md` «Rate limiting y operación», deuda en `memoria.md` |
| Headers de seguridad y OpenAPI | `tests/test_security_headers.py` (completo), prueba manual |
| Logs de 401/429 con `request_id`, `reason` y fingerprint | `test_each_401_reason_is_logged`, `test_429_logs_request_id_reason_client_and_retry`, `test_credentials_and_body_never_appear_in_logs`, `test_json_formatter_emits_only_allowlisted_extra_fields` |
| Escaneo documentado y `pip-audit` en CI | `tests/test_ci_security.py`, sección «Configuración de GitHub» |
| Sin secretos, PII ni tokens | búsquedas de secretos, `SecretStr`, allowlist de logs |

## Desviaciones del plan

- **Headers en errores 500.** Una excepción no controlada se renderiza en
  `ServerErrorMiddleware`, fuera de la pila de middleware de usuario, por lo que
  `SecurityHeadersMiddleware` no podía añadir las cabeceras al 500. Se centralizó el
  mapa en `SECURITY_RESPONSE_HEADERS` (`api/errors.py`) y `error_response()` lo aplica
  también; el middleware importa esa misma constante. El sobre de error no cambió.
- **Re-enganche de `caplog` en tests.** `create_app()` llama a `configure_logging()`,
  que limpia los handlers del root y retira el handler de `caplog`. El helper `_capture`
  en `tests/test_security_logging.py` lo vuelve a añadir para poder asertar los eventos.
- **`api/routes/generative.py`** se tocó en B4 para fijar el orden de dependencias
  (`require_service_key` antes que `enforce_rate_limit`), aunque no figuraba en la lista
  inicial de archivos del plan.
- **Corpus de texto largo** representado con `"repeat": 10000` en lugar de literalizar 30 000
  caracteres; el loader del test lo expande.
- **Tabla de confusables** expresada como puntos de código: ruff `RUF001` rechaza los
  caracteres cirílicos/griegos literales en cadenas.

## Confirmación de secretos y PII

- Búsqueda del prefijo de clave de Google en archivos versionados: sin coincidencias.
- Búsqueda del secreto de prueba local en archivos versionados: sin coincidencias.
- Los comandos concretos no se literalizan aquí para no introducir una coincidencia
  autorreferencial.
- `GENAI_SERVICE_KEY`, `GENAI_SERVICE_KEY_PREVIOUS` y `GENAI_API_KEY` se modelan como
  `SecretStr`; no aparecen en `repr`, logs, prompts ni respuestas.
- `.env` no está versionado; `.env.example` solo contiene variables vacías y comentarios.
- Los logs de `auth.rejected` y `rate_limit.rejected` llevan un `reason` acotado y un
  fingerprint; nunca la clave presentada ni el body.
- El contrato no incluye nombre del propietario, dirección exacta ni tokens de usuario.

## Fuera de esta spec

Quedan fuera de alcance mTLS, autenticación de usuarios, moderación (006), observabilidad
avanzada (007), HSTS/CSP en la aplicación, presupuesto global de tokens y despliegue.
El runbook es el apéndice de `spec.md`.
