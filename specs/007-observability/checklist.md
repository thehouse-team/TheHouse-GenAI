# Checklist — 007-observability Observabilidad

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Schema de logs documentado y probado.
- [ ] Métricas expuestas internamente con nombres estables.
- [ ] Trazas correlacionan una request completa.
- [ ] SLOs y alertas aprobados.
- [ ] Pruebas garantizan ausencia de contenido sensible.
- [ ] Coste/tokens medidos sin almacenar texto.

## Seguridad

- [ ] No incluir contenido de prompts/respuestas en logs, métricas ni trazas.
- [ ] No incluir headers de autenticación.
- [ ] Limitar cardinalidad de etiquetas para evitar PII.
- [ ] Proteger endpoint de métricas en red interna.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
