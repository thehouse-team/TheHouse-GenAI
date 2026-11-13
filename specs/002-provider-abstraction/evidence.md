# Evidencia — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-13
- **Rama:** `feature/provider-abstraction`
- **Entorno:** Windows, Python 3.12.10 (`.venv` del proyecto)

## Comandos y resultados

| Comando | Resultado |
| --- | --- |
| `python --version` (venv) | `Python 3.12.10` |
| `ruff check .` | `All checks passed!` |
| `mypy src` | `Success: no issues found in 18 source files` |
| `pytest` | `148 passed, 1 warning in 0.53s` |
| `git diff --check` | Sin errores de whitespace (código 0) |

El único warning es `StarletteDeprecationWarning` de `fastapi.testclient` al usar
`httpx`; es preexistente de la spec 001 y no lo introduce G02. Queda anotado como
deuda para la spec 008.

Reparto de los 148 tests:

| Archivo | Tests |
| --- | --- |
| `tests/test_providers.py` | 102 |
| `tests/test_config.py` | 20 |
| `tests/test_import_boundaries.py` | 9 |
| `tests/test_provider_factory.py` | 8 |
| `tests/test_errors.py` | 5 |
| `tests/test_health.py` | 4 |

## Criterio de aceptación y evidencia

| Criterio | Evidencia |
| --- | --- |
| Puerto y DTOs aprobados, tipados en modo estricto | `providers/base.py`; `mypy src` sin errores en 18 archivos; `test_request_is_immutable`, `test_response_is_immutable`, `test_usage_is_immutable` |
| Test de frontera: application/domain no importan httpx ni SDKs | `test_source_tree_has_no_forbidden_imports` (AST de todo `src/thehouse_genai/`); `test_detector_reports_a_forbidden_import` y `test_detector_reports_a_provider_sdk_import` prueban que el detector no es vacío |
| Timeout determinista con el fake, con `ProviderTimeoutError` | `test_guard_converts_injected_timeout_error`, `test_guard_converts_real_timeout` (`hang=True`, 0,05 s), `test_fake_hang_never_answers` |
| Errores normalizados sin filtrar detalles internos | `test_guard_propagates_provider_error_unchanged`, `test_guard_normalizes_generic_exception`, `test_guard_normalizes_validation_error`, `test_guard_error_does_not_leak_prompt_or_vendor_detail`, `test_error_messages_are_fixed_and_not_empty` |
| `FakeProvider` cubre éxito, error y timeout | `test_fake_returns_programmed_response`, `test_fake_raises_programmed_taxonomy_error`, `test_fake_raises_programmed_generic_error`, `test_fake_hang_never_answers` |
| La factory rechaza proveedores distintos de `fake` | `test_factory_rejects_unsupported_provider` (inyectado con `Settings.model_construct`), `test_factory_rejects_missing_provider`, `test_supported_providers_is_only_fake` |
| Entrada sobredimensionada produce `ProviderInputTooLargeError` antes de invocar el puerto | `test_guard_rejects_oversized_input_without_calling_provider` (`fake.calls == []`), `test_guard_accepts_input_at_the_limit`, `test_guard_counts_system_prompt_in_the_limit` |
| Configuración incompleta o inválida falla al iniciar | `test_genai_provider_rejects_unsupported_value`, `test_genai_provider_defaults_to_none`, `test_genai_provider_empty_string_is_none`, `test_genai_provider_is_normalized` |

Evidencia adicional de seguridad:

| Requisito | Evidencia |
| --- | --- |
| Sin secretos ni PII | `test_factory_error_does_not_leak_the_api_key`, `test_factory_error_does_not_leak_the_api_key_for_unsupported_provider`, `test_api_key_is_not_exposed_in_repr` (001) |
| Sin red en la suite | fixture autouse `block_network` en `tests/conftest.py`; `test_network_block_rejects_external_connection`, `test_network_block_rejects_external_dns`, `test_network_block_allows_loopback` |
| DTOs cerrados y acotados | `test_request_rejects_unknown_field`, `test_response_rejects_unknown_field`, `test_usage_rejects_unknown_field`, `test_request_rejects_invalid_temperature`, `test_request_rejects_invalid_max_output_tokens` |

## Commits de la rama

```
0c864a7 feat: add provider factory, import boundaries and offline test guard
eee3195 feat: add guarded provider with timeout and input limit
98d90b4 feat: add provider protocol and fake provider
dd81f26 feat: add provider DTOs and error taxonomy
7a6e3e2 feat: validate genai provider setting (fake only)
53bbbea docs: activate spec 002 and record design decisions
```

La referencia final es el pull request con squash hacia `main`; se completa al
mergear.

## Verificaciones de límites

- No se creó ningún adaptador real ni se integró un SDK de proveedor.
- No se añadió ninguna llamada de red: la suite corre con el guard de red activo.
- No se añadieron dependencias: `pyproject.toml` no cambió.
- No se tocó `domain/` ni `application/`.
- No se registran prompts, respuestas ni cuerpos de request; G02 no añadió logging.
- No hay reintentos ni circuit breaker.
- Fixtures sintéticos, sin datos reales.

## Desviaciones respecto al plan original

- El orden de los bloques se ajustó durante la ejecución: T9 (Protocol) y T8
  (`FakeProvider`) se implementaron antes que T7 (guard), para poder probar el doble de
  test sin depender del guard.
- El guard quedó en `providers/base.py` (D-11), dentro de los archivos previstos.
- Los tests async usan `asyncio.run` en lugar de `pytest-asyncio` (D-4), por lo que
  `pyproject.toml` no se modificó.
- La red de los tests se bloquea solo hacia destinos no-loopback, sin sustituir
  `socket.socket` ni impedir la creación de sockets, porque `asyncio.run` usa
  `socketpair`, que en Windows conecta a `127.0.0.1`.
- `GENAI_API_KEY=` y `GENAI_MODEL=` vacíos quedan como `SecretStr('')` y `''` en lugar
  de `None`; es comportamiento heredado de 001 y se normaliza en 011.

## Pendiente fuera de G02

- Pull request con squash hacia `main` (tarea T13).
- Logging estructurado de las llamadas al proveedor: spec 007.
- Evaluación de proveedores y adaptador real: spec 011.
- `StarletteDeprecationWarning` de `TestClient`: spec 008.
