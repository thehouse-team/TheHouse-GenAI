# Checklist — 006-moderation Moderación de contenido

- **Estado:** ACTIVE
- **Alcance:** A (salida generativa + `safetySettings`)

## Criterios de aceptación

- [ ] Política `moderation_v1` aprobada, versionada y probada.
- [ ] Puerto, fake y moderador local probados sin red.
- [ ] Correo, teléfono y URL en la salida degradan a fallback y no llegan al cliente.
- [ ] Léxico ofensivo es-MX por palabra completa, con allowlist de colisiones.
- [ ] El corpus benigno versionado de rentas estudiantiles no se bloquea.
- [ ] Salida adversa o error del moderador respeta el fail-closed (A2).
- [ ] Logs solo con metadatos permitidos; ningún texto moderado aparece en logs.
- [ ] `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE` presente en el payload, sin llamada
      extra y sin contenido en logs.
- [ ] La plantilla de fallback no incluye el título de la propiedad (A6).
- [ ] El contrato `{explanation, generated, promptVersion}` no cambia.
- [ ] `ruff check .`, `mypy src` y `pytest` en verde, sin red.

## Seguridad

- [ ] No registrar texto moderado ni motivos detallados con PII.
- [ ] Minimizar datos enviados al moderador (moderador local: el texto no sale del proceso).
- [ ] Limitar el tamaño del texto a moderar (900 caracteres).
- [ ] Separar decisión de moderación de generación para poder auditarla.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
