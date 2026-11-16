# Evidencia — 011-llm-provider Proveedor LLM real

- **Estado:** ACTIVE
- **Fecha:** 2026-11-15
- **Implementación:** no iniciada (spec activada; bloque B1 en curso)

## Resultado

Spec activada el 2026-11-15 con el plan aprobado. El bloque B1 (activación,
evaluación y decisión) está cerrado: existen `evaluation.md` con la matriz de los
seis criterios y sus fuentes, y `decision.md` con el proveedor elegido, las
alternativas descartadas, las decisiones de integración D-1 a D-14 y las condiciones
de revisión.

No existe todavía implementación, adaptador ni script de smoke test, y por tanto no
hay evidencia de ejecución que reportar. La spec no se marca como completada hasta
cumplir sus criterios.

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
