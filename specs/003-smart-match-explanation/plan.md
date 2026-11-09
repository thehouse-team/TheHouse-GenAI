# Plan — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction

## Enfoque técnico

1. Definir schemas Pydantic de entrada/salida antes de cualquier prompt.
2. Construir un contexto serializado solo con campos allowlist.
3. Solicitar explicación breve y `facts_used`; validar que cada hecho exista.
4. Extraer números de la salida y comprobar que coincidan con la entrada.
5. Usar fake provider para probar guardrails sin depender del modelo.
6. Mapear fallos de generación a 502 sin filtrar detalles del proveedor.

## Pasos previstos

1. Aprobar contrato y allowlist de hechos.
2. Implementar schemas y validaciones de entrada.
3. Implementar constructor de contexto y prompt con delimitadores.
4. Implementar validador de salida y `facts_used`.
5. Crear caso de uso y endpoint autenticado.
6. Añadir pruebas de fidelidad, límites e inyección.
7. Actualizar SDD y evidencia.

## Archivos previstos

- `src/thehouse_genai/domain/match_explanation.py`
- `src/thehouse_genai/application/explain_match.py`
- `src/thehouse_genai/api/routes/generative.py`
- `tests/test_explain_match.py`

## Estrategia de pruebas

- Fixture canónica produce explicación válida y breve.
- Datos faltantes o score inválido producen 422.
- Salida con número/servicio inventado se rechaza.
- Intento de prompt injection no altera hechos.
- Timeout/error del proveedor produce 502 seguro.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Alucinación de servicios o precios | Validación determinista contra hechos de entrada. |
| El modelo recalcula el score | Score fuera del prompt generativo y salida sin score. |
| Prompt injection en descripciones | Delimitadores, allowlist y validación de salida. |
| Exposición de PII | Contrato mínimo y filtro previo a GenAI. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
