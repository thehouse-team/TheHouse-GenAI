# Tareas — 007-observability Observabilidad

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Diseño

- [ ] Aprobar schema de logs y métricas.
- [ ] Definir SLOs, alertas y retención.

## Implementación

- [ ] Instrumentar middleware y casos de uso.
- [ ] Instrumentar proveedor y tokens.
- [ ] Implementar propagación de contexto.

## Pruebas y cierre

- [ ] Añadir pruebas de métricas y no-fuga.
- [ ] Validar dashboards/alertas en staging.
- [ ] Actualizar evidencia.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
