# Checklist — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** IMPLEMENTED
- **Fecha de cierre:** 2026-11-13

## Criterios de aceptación

- [x] Puerto y DTOs aprobados, tipados en modo estricto.
- [x] Test de frontera: application/domain no importan httpx ni SDKs de proveedor.
- [x] Timeout verificado de forma determinista con el fake; el puerto expone
      `ProviderTimeoutError`.
- [x] Errores normalizados a la taxonomía propia (`ProviderAuthError`,
      `ProviderRateLimitError`, `ProviderUnavailableError`,
      `ProviderInvalidResponseError`) sin filtrar detalles internos.
- [x] `FakeProvider` cubre éxito, error y timeout.
- [x] La factory rechaza proveedores distintos de `fake` en G02.
- [x] Entrada que excede `GENAI_MAX_INPUT_CHARS` produce `ProviderInputTooLargeError`
      antes de invocar el puerto.
- [x] Configuración incompleta o inválida falla al iniciar.

## Seguridad

- [x] No registrar prompts ni respuestas completas por defecto; solo metadatos.
- [x] Redactar cualquier clave o cabecera sensible en logs y excepciones.
- [x] Validar tamaño y campos permitidos antes de invocar el proveedor.
- [x] Sin reintentos en esta spec para no amplificar coste ni latencia.
- [x] Sin red, credenciales ni datos reales en fixtures.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `pytest` en verde y sin red.
- [x] Sin secretos, PII ni tokens en código, logs o fixtures.
- [x] Sin adaptadores ni proveedores reales fuera de alcance.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.

## Corrección G10 (2026-11-26)

- [x] `provider.call.failed` registra `http_status` o `transport_error`, sin cuerpo ni
      mensaje del vendor.
- [x] El adaptador de Gemini no importa `api.request_context`; el `request_id` sigue
      presente por el filtro de `infrastructure/logging.py`.
- [x] Un reintento acotado aplicado por la factory a explain-match y parse-search, solo
      ante `PROVIDER_UNAVAILABLE`, con sleep inyectado.
- [x] Sin reintento ante Auth, `PROVIDER_RATE_LIMIT` (429 de cuota por minuto),
      InvalidResponse, Timeout, primer intento lento, plazo excedido o presupuesto
      agotado; cada intento consumido reserva su cupo diario.
- [x] La reserva del reintento ocurre tras la comprobación del plazo posterior al sleep;
      un plazo vencido no consume cupo.
- [x] `provider.call.retry` con `attempt`, `error_code` y `request_id`; sin etiquetas
      nuevas de métrica.
- [x] Gates en verde y evidencia registrada; spec sigue `IMPLEMENTED`.
