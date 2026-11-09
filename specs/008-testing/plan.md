# Plan — 008-testing Estrategia de pruebas

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction

## Enfoque técnico

1. Mantener pruebas rápidas por capa y pocas integraciones.
2. Compartir fixtures canónicas entre specs 003/004.
3. Probar contratos con JSON Schema/Pydantic.
4. Añadir corpus de ataques y regresiones de seguridad.

## Pasos previstos

1. Documentar estrategia y convenciones.
2. Crear fixtures y fake provider compartido.
3. Añadir contract tests de endpoints futuros.
4. Añadir pruebas de seguridad y regresión.
5. Configurar cobertura y reporte en CI.
6. Actualizar SDD y evidencia.

## Archivos previstos

- `tests/fixtures/`
- `tests/contract/`
- `tests/security/`
- `pyproject.toml`

## Estrategia de pruebas

- Unitarias de dominio y aplicación.
- Contract tests de endpoints generativos.
- Pruebas de seguridad y límites.
- Reporte de cobertura en CI.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Tests frágiles | Fixtures pequeñas y contratos explícitos. |
| Falsa confianza por mocks | Casos de integración con fake provider. |
| Cobertura como objetivo vacío | Enfoque en rutas críticas y guardrails. |
| Flakiness | Sin red, timeouts y datos deterministas. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
