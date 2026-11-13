# 002-provider-abstraction — Abstracción de proveedor LLM

- **Estado:** PLANNED
- **Depende de:** 001-foundation
- **Habilita:** 003, 004, 011
- **Fecha de alta:** 2026-11-08
- **Última revisión:** 2026-11-12

## Objetivo

Definir un puerto LLM neutral (`GenerativeAiProvider`), sus DTOs inmutables, una taxonomía
de errores, un proveedor falso determinista y una factory de selección, de modo que
application y domain nunca dependan de un SDK ni de la red. G02 es 100% offline: no se
integra ningún proveedor real.

## Contexto

Las specs 003 y 004 necesitan invocar un LLM. Sin una interfaz, prompts, SDKs y errores
del proveedor se filtrarían a application/api, dificultando pruebas, cambios de proveedor
y control de secretos. La evaluación de proveedores y el adaptador real viven en
`011-llm-provider` (G03); esta spec construye solo el contrato y el doble de test.

## Alcance

### Incluido

- Protocolo `GenerativeAiProvider` y DTOs inmutables (`GenerativeAiRequest`,
  `GenerativeAiResponse`, `GenerativeAiUsage`).
- Taxonomía de errores propia (`ProviderTimeoutError`, `ProviderAuthError`,
  `ProviderRateLimitError`, `ProviderUnavailableError`, `ProviderInvalidResponseError`,
  `ProviderInputTooLargeError`).
- `FakeProvider` determinista para tests, con fallos programables y sin acceso a red.
- Factory de selección por configuración validada; en G02 solo admite `fake`.
- Timeout obligatorio en el puerto y límite de entrada con `GENAI_MAX_INPUT_CHARS`.
- Contrato de `Settings` para proveedor, modelo, timeout y límite de entrada.

### Excluido

- Adaptador HTTP, SDK de proveedor, llamadas de red y credenciales reales (spec 011).
- Prompts de negocio, endpoints generativos, moderación, streaming, tools y embeddings.
- Reintentos automáticos o circuit breaker (se deciden en specs posteriores).

## Requisitos

- **RF-01:** application y domain dependen solo del puerto, nunca de httpx ni de un SDK.
- **RF-02:** el request es inmutable, validado y acotado antes de salir del proceso.
- **RF-03:** toda invocación declara timeout y el puerto se cancela al excederlo.
- **RF-04:** los errores se normalizan a la taxonomía propia; nunca se devuelve el detalle.
- **RF-05:** el fake permite probar éxito, error y timeout sin red.
- **RF-06:** la API key se modela como `SecretStr` y no aparece en logs, `repr` ni
  respuestas.
- **RF-07:** configuración incompleta o inválida falla claramente al arrancar.
- **RF-08:** la factory no puede construir un proveedor real en G02; solo `fake`.
- **RF-09:** una entrada que exceda `GENAI_MAX_INPUT_CHARS` se rechaza con
  `ProviderInputTooLargeError` antes de invocar el puerto.

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

## Seguridad y privacidad

- No registrar prompts ni respuestas completas por defecto; solo metadatos.
- Redactar cualquier clave o cabecera sensible en logs y excepciones.
- Validar tamaño y campos permitidos antes de invocar el proveedor.
- Sin reintentos en esta spec para no amplificar coste ni latencia.
- Sin red, sin credenciales y sin datos reales en fixtures.

## Fuera de esta spec

Esta spec permanece `PLANNED` hasta que sea su turno. No se activa hasta que la
enmienda 1.1 de la constitución, el plan y el contrato del puerto estén aprobados.
