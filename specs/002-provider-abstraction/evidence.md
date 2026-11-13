# Evidencia — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED
- **Fecha:** —
- **Implementación:** no iniciada

## Resultado

Spec planificada. No existe implementación, ejecución de pruebas ni evidencia que
reportar. No se debe marcar como completada hasta cumplir sus criterios.

## Evidencia requerida al cerrar

- [ ] Puerto y DTOs aprobados, tipados en modo estricto.
- [ ] Test de frontera: application/domain no importan httpx ni SDKs de proveedor.
- [ ] Timeout verificado de forma determinista con el fake; el puerto expone
      `ProviderTimeoutError`.
- [ ] Errores normalizados a la taxonomía propia (`ProviderAuthError`,
      `ProviderRateLimitError`, `ProviderUnavailableError`,
      `ProviderInvalidResponseError`) sin filtrar detalles internos.
- [ ] `FakeProvider` cubre éxito, error y timeout.
- [ ] La factory rechaza proveedores distintos de `fake` en G02.
- [ ] Entrada que excede `GENAI_MAX_INPUT_CHARS` produce `ProviderInputTooLargeError`
      antes de invocar el puerto.
- [ ] Configuración incompleta o inválida falla al iniciar.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
