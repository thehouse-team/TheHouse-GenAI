# Tareas — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Contrato y diseño

- [ ] Aprobar schemas de entrada y salida.
- [ ] Definir allowlist de hechos y límite de palabras.
- [ ] Definir política de errores y PII.

## Implementación

- [ ] Implementar validaciones de dominio.
- [ ] Implementar prompt y caso de uso.
- [ ] Implementar endpoint y autenticación de servicio.
- [ ] Implementar validador de fidelidad de salida.

## Pruebas y cierre

- [ ] Añadir pruebas de fidelidad e inyección.
- [ ] Añadir pruebas de error y timeout.
- [ ] Ejecutar gates y actualizar evidencia.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
