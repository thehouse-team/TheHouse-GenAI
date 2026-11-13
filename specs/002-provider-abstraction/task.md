# Tareas — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Diseño

- [ ] Aprobar DTOs y firma del protocolo `GenerativeAiProvider`.
- [ ] Definir taxonomía de errores (`ProviderTimeoutError`, `ProviderAuthError`,
      `ProviderRateLimitError`, `ProviderUnavailableError`,
      `ProviderInvalidResponseError`, `ProviderInputTooLargeError`) y política de timeout.
- [ ] Definir estrategia de inyección, configuración y factory.

## Implementación

- [ ] Crear `providers/base.py` con protocolo, DTOs y errores.
- [ ] Implementar `FakeProvider` determinista.
- [ ] Implementar `providers/factory.py` con validación del proveedor soportado.
- [ ] Validar proveedor, modelo, timeout y límite de entrada en `Settings`.

## Pruebas

- [ ] Añadir tests de contrato, timeout, errores y límite de entrada.
- [ ] Añadir test de frontera de imports (sin httpx ni SDKs).
- [ ] Añadir test que verifique que la suite no usa red.

## Cierre

- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Actualizar `checklist.md`, `evidence.md` y `memoria.md` con resultados reales.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
