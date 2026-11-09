# Plan — 010-integration-thehouse Integración con TheHouse Backend

- **Estado:** PLANNED
- **Depende de:** 002, 003, 004, 005, 007, 008

## Enfoque técnico

1. Definir contrato y auth conjuntamente con Backend.
2. Implementar cliente resiliente en Backend, no en GenAI.
3. Validar en staging con datos sintéticos.
4. Desplegar gradualmente con métricas y criterio de aborto.

## Pasos previstos

1. Acordar contratos y autenticación.
2. Implementar cliente Backend con timeouts y breaker.
3. Añadir filtro PII y correlación.
4. Ejecutar contract tests y E2E staging.
5. Definir rollout, métricas y rollback.
6. Actualizar SDD y evidencia.

## Archivos previstos

- `Contrato OpenAPI exportado`
- `Pruebas de contrato en Backend y GenAI`
- `Runbook operativo`

## Estrategia de pruebas

- Contract tests de ambos endpoints.
- Auth inválida y ausente.
- Timeout, 429, 5xx y circuit breaker.
- Fallback del Backend.
- E2E staging con datos sintéticos.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Acoplamiento de contratos | Versionado y contract tests. |
| Cascada por lentitud | Timeouts, circuit breaker y fallback. |
| PII en tránsito | Filtro y revisión conjunta. |
| Rollout defectuoso | Canary, métricas y rollback. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
