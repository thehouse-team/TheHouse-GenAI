# Evidencia — 011-llm-provider Proveedor LLM real

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-16
- **Implementación:** completa (bloques B1 a B9)

## Resultado

Spec activada el 2026-11-15 con el plan aprobado y cerrada el 2026-11-16 tras el
smoke test manual. Existen `evaluation.md` con la matriz de los seis criterios y sus
fuentes, `decision.md` con el proveedor elegido, las alternativas descartadas, las
decisiones de integración D-1 a D-20 y las condiciones de revisión, el adaptador
`GeminiProvider` detrás del puerto, su registro en la factory y el script de smoke
test manual.

## Smoke test manual (B8)

- **Fecha:** 2026-11-16
- **Modelo:** `gemini-3.5-flash-lite` (familia Flash Lite)
- **Capa:** gratuita, proyecto `thehouse-genai` en Google AI Studio
- **Ejecución:** manual y opt-in, fuera de CI, con confirmación explícita
- **Datos:** prompts sintéticos de una vivienda ficticia; sin datos reales ni PII

| Caso | Iteraciones | Latencia min (ms) | Latencia mediana (ms) | Latencia max (ms) | Tokens entrada | Tokens salida | finish_reason | Aviso de deprecación | Errores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A · texto en español | 3 | 1309.2 | 1445.0 | 1461.3 | 97 | 63 | STOP | no | - |
| B · salida JSON | 3 | 817.0 | 1047.4 | 1171.6 | 99 | 59 | STOP | no | - |

### Observaciones

- El español es natural y usa solo los datos del prompt, sin inventar hechos. Único
  defecto detectado: un espacio faltante ("conuna").
- El JSON devuelto fue válido y con los cinco campos pedidos.
- Ninguna llamada falló: las seis respostas con `finish_reason` `STOP`.
- La credencial no aparece en la salida del script.
- `.env` confirmado como ignorado por git: `git check-ignore -v .env` →
  `.gitignore:2:.env`.
- Ninguna llamada devolvió aviso de deprecación, con lo que `temperature` se aplicó
  sin observancia en este modelo.

### Límites observados del modelo (capa gratuita, vistos en AI Studio)

| Métrica | Valor |
| --- | --- |
| Requests por minuto (RPM) | ~15 |
| Tokens por minuto (TPM) | 250K |
| Requests por día (RPD) | 500 |

### Observación menor

- La confirmación interactiva del script acepta «si» en minúsculas, porque la
  comparación normaliza a mayúsculas. Queda anotado como deuda menor y no se corrige
  en esta spec.

## Evidencia requerida al cerrar

- [x] Matriz de evaluación con los seis criterios y fuentes citadas.
- [x] Documento de decisión aprobado.
- [x] Adaptador implementando `GenerativeAiProvider` y registrado en la factory.
- [x] Test de contrato del adaptador en verde, sin red.
- [x] Errores del vendor mapeados a la taxonomía propia.
- [x] La credencial no aparece en logs, `repr` ni respuestas.
- [x] Timeout y límite de entrada verificados.
- [x] El modelo y su versión aparecen en logs internos y en ninguna respuesta de la API.
- [x] Script de smoke test manual documentado y no ejecutado por CI.
- [x] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [x] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [x] Referencia al commit que implementa la spec.

## Gates de cierre (2026-11-16)

| Gate | Comando | Resultado |
| --- | --- | --- |
| Lint | `.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` |
| Tipos (src) | `.venv\Scripts\python.exe -m mypy src` | `Success: no issues found in 19 source files` |
| Tipos (script) | `.venv\Scripts\python.exe -m mypy --strict scripts/smoke_provider.py` | `Success: no issues found in 1 source file` |
| Tests | `.venv\Scripts\python.exe -m pytest` | `279 passed, 1 warning in 1.78s` |
| Whitespace | `git diff --check` | Sin salida: limpio |
| Caracteres fuera de rango | `git grep -n -P "[\x{4E00}-\x{9FFF}]"` | Sin coincidencias |

El único warning es el `StarletteDeprecationWarning` de `TestClient` con `httpx`, ya
registrado como deuda para la spec 008.

### Reparto de los 279 tests

| Fichero | Tests |
| --- | --- |
| `tests/test_providers.py` | 102 |
| `tests/test_provider_adapter.py` | 57 |
| `tests/test_import_boundaries.py` | 53 |
| `tests/test_config.py` | 33 |
| `tests/test_provider_factory.py` | 17 |
| `tests/test_smoke_script.py` | 8 |
| `tests/test_errors.py` | 5 |
| `tests/test_health.py` | 4 |

## Commits de la spec

```text
13ec6c5 docs: record gemini smoke test evidence
6d47039 feat: add manual gemini smoke test script
d669afd test: harden import boundaries for providers and scripts
dc9aef7 feat: register the gemini provider in the factory
11e5d64 feat: map gemini http errors and add provider call logging
11096f7 feat: add gemini provider request and response mapping
b89892f feat: require gemini credentials in settings
f0efbec docs: activate spec 011 with provider evaluation and decision
```

## Mapeo de criterios de aceptación a tests

| Criterio | Verificado por |
| --- | --- |
| Matriz de evaluación con los seis criterios y fuentes | `specs/011-llm-provider/evaluation.md` (revisión documental) |
| Documento de decisión aprobado | `specs/011-llm-provider/decision.md` (revisión documental) |
| Adaptador que implementa `GenerativeAiProvider` | `test_provider_satisfies_the_port_protocol`, `test_provider_adapter.py` |
| Respuesta del vendor validada y normalizada | `test_response_maps_text_usage_and_finish_reason`, `test_response_maps_the_provider_model_from_the_vendor`, `test_response_joins_every_text_part`, `test_truncated_answer_is_not_an_error` |
| Errores 401/429/5xx mapeados | `test_http_status_is_mapped_to_the_taxonomy`, `test_timeout_is_mapped_to_the_timeout_error`, `test_network_error_is_mapped_to_unavailable` |
| La credencial no aparece en logs, `repr` ni respuestas | `test_repr_does_not_expose_the_credential`, `test_credential_travels_only_in_the_header`, `test_vendor_body_never_reaches_the_exception`, `test_credential_never_reaches_the_exception_chain`, `test_success_log_records_metadata_without_content`, `test_failure_log_records_the_error_code_without_detail` |
| Timeout y límite de entrada verificados | `test_timeout_is_mapped_to_the_timeout_error`, `test_factory_applies_the_timeout_for_gemini`, `test_factory_applies_the_input_limit_for_gemini`, `test_factory_applies_the_input_limit_from_settings` |
| Proveedor registrado en la factory y validado en `Settings` | `test_factory_builds_a_guarded_gemini_provider`, `test_supported_providers_are_fake_and_gemini`, `test_gemini_without_api_key_is_rejected`, `test_gemini_without_model_is_rejected` |
| Tests del adaptador en verde y sin red | Toda la suite, con el guard de red de `tests/conftest.py` activo |
| El modelo solo en logs internos | `test_success_log_records_metadata_without_content`, `test_json_logging_emits_the_provider_metadata`, `git grep provider_model -- src/thehouse_genai/api/` sin coincidencias |
| Script de smoke test manual opt-in y fuera de CI | `test_script_refuses_to_run_in_ci`, `test_script_requires_the_opt_in_flag`, `test_ci_workflow_never_runs_the_smoke_script`, `test_smoke_script_exists_outside_the_test_suite` |
| Frontera de imports | `test_source_tree_has_no_forbidden_imports`, `test_only_the_gemini_adapter_imports_httpx`, `test_scripts_have_no_forbidden_imports`, `test_detector_rejects_every_forbidden_dependency`, `test_importing_the_port_does_not_load_httpx` |

## Desviaciones del plan

1. **B6 adelantado a B3.** El adaptador introduce el primer import del cliente HTTP y
   el test de fronteras lo prohíbe, de modo que la suite quedaba en rojo. En B3 se
   aplicó el ajuste mínimo (allowlist de `httpx` solo en `providers/gemini.py` y
   `gemini` como implementación prohibida en `application`); B6 endureció el barrido
   con el test parametrizado por SDK y la cobertura de `scripts/`.
2. **`py.typed` y `pyproject.toml`.** `mypy --strict scripts/smoke_provider.py` no
   podía analizar el paquete instalado sin el marcador PEP 561. Se añadió
   `src/thehouse_genai/py.typed` y su declaración en `[tool.setuptools.package-data]`.
   Es la única modificación de `pyproject.toml` en la spec.
3. **Separación de los commits de B5 y B6.** B5 quedó commiteado como
   `dc9aef7 feat: register the gemini provider in the factory` y B6 como
   `d669afd test: harden import boundaries for providers and scripts`, en lugar de un
   único commit, para que cada bloque tenga su propio registro.
4. **Nombre del adaptador.** `providers/gemini.py`, en lugar del marcador
   `<vendor>_provider.py` del plan, en coherencia con `fake.py` y `factory.py`.

## Revisión de seguridad

- Sin secretos versionados: una búsqueda del prefijo de la clave del vendor en todo el
  repositorio no devuelve nada, y `git ls-files` solo lista `.env.example`.
- `.env` ignorado por git: `git check-ignore -v .env` → `.gitignore:2:.env`.
- La credencial es `SecretStr`, viaja solo en la cabecera `x-goog-api-key` y no aparece
  en logs, `repr`, excepciones ni en la URL.
- Los logs solo llevan metadatos: proveedor, modelo interno, código de error,
  duración y longitudes. Nunca prompts, respuestas, cabeceras ni cuerpos.
- Los prompts del smoke test usan datos sintéticos de una vivienda ficticia: sin PII
  ni datos reales.
- Sin red en CI: la suite corre con el guard de red activo y el script manual se
  niega a ejecutarse si la variable `CI` está activa.
