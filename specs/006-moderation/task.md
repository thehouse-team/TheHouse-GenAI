# Tareas — 006-moderation Moderación de contenido

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Política

- [ ] Redactar taxonomía y severidad.
- [ ] Aprobar política y comportamiento fail-closed.

## Implementación

- [ ] Definir puerto y DTOs de moderación.
- [ ] Implementar moderador fake.
- [ ] Integrar moderación en el pipeline generativo.

## Pruebas y cierre

- [ ] Añadir pruebas de moderación y errores.
- [ ] Verificar ausencia de contenido en logs.
- [ ] Actualizar evidencia.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
