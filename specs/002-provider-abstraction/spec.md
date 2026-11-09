# 002-provider-abstraction — Abstracción de proveedor LLM

- **Estado:** PLANNED
- **Depende de:** 001-foundation
- **Habilita:** 003, 004, 008
- **Fecha de alta:** 2026-11-08

## Objetivo

Definir un puerto LLM neutral y un adaptador HTTP sustituible, con un proveedor falso determinista para pruebas, sin acoplar la aplicación a ningún vendor.

## Contexto

Las specs 003 y 004 necesitan invocar un LLM. Sin una interfaz, prompts, SDKs y errores del proveedor se filtrarían a application/api, dificultando pruebas, cambios de proveedor y control de secretos.

## Alcance

### Incluido

- Puerto `LLMProvider` y DTOs inmutables (`LLMRequest`, `LLMResponse`, `LLMUsage`).
- Selección de proveedor y modelo mediante configuración validada.
- Adaptador HTTP basado en httpx con cliente inyectable y timeout obligatorio.
- `FakeLLMProvider` determinista para tests, sin acceso a red.
- Taxonomía de errores del proveedor y mapeo a errores seguros de la API.
- Validación de tamaño de entrada con `GENAI_MAX_INPUT_CHARS`.

### Excluido

- Prompts de negocio, endpoints generativos, moderación, streaming, tools y embeddings.
- Credenciales reales, llamadas a producción y despliegue.
- Reintentos automáticos o circuit breaker (se deciden en specs posteriores).

## Requisitos

- **RF-01:** application y domain dependen solo del puerto, nunca de httpx ni de un SDK.
- **RF-02:** el request es inmutable, validado y acotado antes de salir del proceso.
- **RF-03:** toda llamada tiene timeout y se cancela al excederlo.
- **RF-04:** errores del proveedor se normalizan; nunca se devuelve el cuerpo crudo.
- **RF-05:** el fake permite probar éxito, error y timeout sin red.
- **RF-06:** la API key usa `SecretStr` y no aparece en logs, `repr` ni respuestas.
- **RF-07:** configuración incompleta falla claramente al arrancar.

## Criterios de aceptación

- [ ] Interfaz y DTOs aprobados, tipados en modo estricto.
- [ ] Test de frontera: application/domain no importan httpx ni SDKs de proveedor.
- [ ] Timeout verificado con transporte simulado.
- [ ] Errores 401/429/5xx del proveedor mapeados sin filtrar detalles internos.
- [ ] Fake provider cubre éxito, error y timeout.
- [ ] Configuración incompleta o inválida falla al iniciar.

## Seguridad y privacidad

- No registrar prompts ni respuestas completas por defecto; solo metadatos.
- Redactar `Authorization` y cualquier clave en logs y excepciones.
- Validar tamaño y campos permitidos antes de enviar al proveedor.
- Sin reintentos en esta spec para no amplificar coste ni latencia.

## Fuera de esta spec

No se implementa nada de este documento en G01. La spec permanece PLANNED hasta que
el Backend, la seguridad y los contratos estén aprobados y sea su turno.
