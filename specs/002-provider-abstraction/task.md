# Tareas — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** IMPLEMENTED
- **Fecha de cierre:** 2026-11-13

> La spec estuvo `ACTIVE` del 2026-11-12 al 2026-11-13 con su plan aprobado.
> Las decisiones de diseño (D-1 a D-15) están en `spec.md`.

## Diseño

- [x] Aprobar DTOs y firma del protocolo `GenerativeAiProvider`.
- [x] Definir taxonomía de errores (`ProviderTimeoutError`, `ProviderAuthError`,
      `ProviderRateLimitError`, `ProviderUnavailableError`,
      `ProviderInvalidResponseError`, `ProviderInputTooLargeError`) y política de timeout.
- [x] Definir estrategia de inyección, configuración y factory.

## Implementación

- [x] Crear `providers/base.py` con protocolo, DTOs y errores.
- [x] Implementar `FakeProvider` determinista.
- [x] Implementar `providers/factory.py` con validación del proveedor soportado.
- [x] Validar proveedor, modelo, timeout y límite de entrada en `Settings`.

## Pruebas

- [x] Añadir tests de contrato, timeout, errores y límite de entrada.
- [x] Añadir test de frontera de imports (sin httpx ni SDKs).
- [x] Añadir test que verifique que la suite no usa red.

## Cierre

- [x] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [x] Actualizar `checklist.md`, `evidence.md` y `memoria.md` con resultados reales.
- [x] Revisar seguridad y ausencia de secretos/PII.
- [x] Cambiar el estado a IMPLEMENTED solo al cumplir todo.

## Detalle por bloque

| Bloque | Tareas | Resultado |
| --- | --- | --- |
| 1 | T1 activación + T2 docstrings | Spec `ACTIVE`; decisiones D-1 a D-15 documentadas en `spec.md` y `plan.md` |
| 2 | T3 `Settings` + T4 `.env.example` | `genai_provider` validado como `Literal["fake"]` opcional y normalizado |
| 3 | T5 DTOs + T6 taxonomía | `providers/base.py` con DTOs inmutables y errores de mensaje fijo |
| 4 | T9 Protocol + T8 `FakeProvider` | Puerto `runtime_checkable` y doble de test determinista |
| 5 | T7 `GuardedProvider` | Límite de entrada y timeout centralizados, con normalización de errores |
| 6 | T10 factory + T11 fronteras | Factory con doble barrera; AST de imports y guard de red en los tests |
| 7 | T12 cierre SDD | Gates en verde, checklist y evidencia actualizados, spec `IMPLEMENTED` |
| 8 | T13 pull request | [ ] Pendiente de apertura y merge por squash; se cierra al mergear |

## Desviaciones respecto al plan original

- El orden de los bloques se ajustó durante la ejecución: el Protocol (T9) y el
  `FakeProvider` (T8) se implementaron antes que el guard (T7), para poder probar el
  doble de test sin depender del guard.
- El guard quedó en `providers/base.py` (D-11), dentro de los archivos previstos.
- Los tests async usan `asyncio.run` en lugar de `pytest-asyncio` (D-4), sin tocar
  `pyproject.toml`.
