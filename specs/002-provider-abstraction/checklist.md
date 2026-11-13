# Checklist — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED

## Criterios de aceptación

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

## Seguridad

- [ ] No registrar prompts ni respuestas completas por defecto; solo metadatos.
- [ ] Redactar cualquier clave o cabecera sensible en logs y excepciones.
- [ ] Validar tamaño y campos permitidos antes de invocar el proveedor.
- [ ] Sin reintentos en esta spec para no amplificar coste ni latencia.
- [ ] Sin red, credenciales ni datos reales en fixtures.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin adaptadores ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
