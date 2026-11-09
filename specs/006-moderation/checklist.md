# Checklist — 006-moderation Moderación de contenido

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Política aprobada y versionada.
- [ ] Puerto e implementación fake probados.
- [ ] Entrada/salida bloqueada no llega al usuario.
- [ ] Error del moderador respeta fail-closed.
- [ ] Logs sin contenido sensible.
- [ ] Pruebas de categorías y falsos positivos.

## Seguridad

- [ ] No registrar texto moderado ni motivos detallados con PII.
- [ ] Minimizar datos enviados al moderador.
- [ ] Limitar tamaño de texto a moderar.
- [ ] Separar decisión de moderación de la generación para poder auditarla.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
