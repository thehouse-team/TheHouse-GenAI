# 010-integration-thehouse — Integración con TheHouse Backend

- **Estado:** PLANNED
- **Depende de:** 002, 003, 004, 005, 007, 008
- **Habilita:** Operación real
- **Fecha de alta:** 2026-11-08

## Objetivo

Integrar GenAI con TheHouse Backend como servicio interno autenticado, con contratos versionados, timeouts, degradación segura y validación en staging.

## Contexto

Android habla con TheHouse Backend; el Backend habla con GenAI. GenAI nunca es llamado directo por el cliente ni recibe PII innecesaria. La integración es la última spec y no se implementa en G01.

## Alcance

### Incluido

- Contrato Backend → GenAI para explain-match y parse-search.
- Autenticación de servicio y versionado de API.
- Timeouts, reintentos acotados y circuit breaker en el Backend.
- Fallback seguro cuando GenAI falla.
- Filtro de PII antes de enviar contexto.
- Pruebas E2E en staging y runbook operativo.
- Plan de rollout y rollback.

### Excluido

- Cambios en Android o exposición directa al cliente.
- Implementar los endpoints (specs 003/004).
- Despliegue real en G01.

## Requisitos

- **RF-01:** solo Backend llama a GenAI, con credencial de servicio.
- **RF-02:** contratos versionados y validados en ambos lados.
- **RF-03:** timeout y circuit breaker evitan cascadas.
- **RF-04:** fallo de GenAI no bloquea la búsqueda ni muestra errores internos.
- **RF-05:** PII mínima y prohibición de tokens/dirección exacta.
- **RF-06:** request ID y trazas correlacionan ambos servicios.
- **RF-07:** rollout gradual con métricas y rollback.

## Criterios de aceptación

- [ ] Contrato aprobado y contract tests en ambos repos.
- [ ] Auth de servicio validada en staging.
- [ ] Timeouts, reintentos y circuit breaker probados.
- [ ] Fallback seguro verificado.
- [ ] E2E staging con datos sintéticos.
- [ ] Runbook y rollback documentados.

## Seguridad y privacidad

- Sin secretos en Android; el cliente nunca conoce la credencial de servicio.
- Filtro de PII antes de la llamada.
- Sin logs de prompts/respuestas completos.
- Rate limit y cuotas alineados con Backend.

## Fuera de esta spec

No se implementa nada de este documento en G01. La spec permanece PLANNED hasta que
el Backend, la seguridad y los contratos estén aprobados y sea su turno.
