# Tareas — 005-security Seguridad de servicio e IA

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Análisis

- [ ] Crear threat model y data flow.
- [ ] Clasificar datos y definir allowlists por endpoint.
- [ ] Definir mecanismo de auth de servicio con Backend.

## Implementación

- [ ] Implementar guard de autenticación.
- [ ] Implementar filtro de PII y redacción.
- [ ] Implementar rate limiting y presupuestos.
- [ ] Integrar escaneos de secretos y dependencias en CI.

## Pruebas y cierre

- [ ] Añadir pruebas negativas de auth y PII.
- [ ] Añadir corpus de prompt injection.
- [ ] Actualizar evidencia y runbook.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
