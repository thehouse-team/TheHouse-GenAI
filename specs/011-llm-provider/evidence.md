# Evidencia — 011-llm-provider Proveedor LLM real

- **Estado:** PLANNED
- **Fecha:** —
- **Implementación:** no iniciada

## Resultado

Spec planificada. No existe implementación, ejecución de pruebas ni evidencia que
reportar. No se debe marcar como completada hasta cumplir sus criterios.

## Evidencia requerida al cerrar

- [ ] Matriz de evaluación con los seis criterios y fuentes citadas.
- [ ] Documento de decisión aprobado.
- [ ] Adaptador implementando `GenerativeAiProvider` y registrado en la factory.
- [ ] Test de contrato del adaptador en verde, sin red.
- [ ] Errores del vendor mapeados a la taxonomía propia.
- [ ] La credencial no aparece en logs, `repr` ni respuestas.
- [ ] Timeout y límite de entrada verificados.
- [ ] El modelo y su versión aparecen en logs internos y en ninguna respuesta de la API.
- [ ] Script de smoke test manual documentado y no ejecutado por CI.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
