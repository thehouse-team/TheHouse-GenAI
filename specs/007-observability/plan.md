# Plan — 007-observability Observabilidad

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction, 005-security

## Enfoque técnico

1. Extender el logging JSON existente con allowlist de campos.
2. Instrumentar middleware, caso de uso y adaptador del proveedor.
3. Propagar request ID y trace ID de forma segura.
4. Definir SLOs antes de elegir backend de observabilidad.

## Pasos previstos

1. Documentar schema de logs y métricas.
2. Instrumentar API, aplicación y proveedor.
3. Implementar propagación de contexto.
4. Definir SLOs, dashboards y alertas.
5. Añadir pruebas de no-fuga.
6. Actualizar SDD y evidencia.

## Archivos previstos

- `src/thehouse_genai/infrastructure/metrics.py`
- `src/thehouse_genai/infrastructure/tracing.py`
- `tests/test_observability.py`

## Estrategia de pruebas

- Logs contienen campos requeridos y request ID.
- Métricas de éxito/error/latencia se incrementan.
- Trazas correlacionan API y proveedor.
- No aparece contenido ni PII en logs/trazas.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| PII en trazas | Allowlist y pruebas de redacción. |
| Coste de observabilidad | Muestreo y retención. |
| Cardinalidad explosiva | Etiquetas acotadas y sin IDs de usuario. |
| Alertas ruidosas | Umbrales y revisión periódica. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
