# Checklist — 006-moderation Moderación de contenido

- **Estado:** IMPLEMENTED
- **Alcance:** A (salida generativa + `safetySettings`)

## Criterios de aceptación

- [x] Política `moderation_v1` aprobada, versionada y probada.
- [x] Puerto, fake y moderador local probados sin red.
- [x] Correo, teléfono y URL en la salida degradan a fallback y no llegan al cliente.
- [x] Léxico ofensivo es-MX por palabra completa, con allowlist de colisiones.
- [x] El corpus benigno versionado de rentas estudiantiles no se bloquea.
- [x] Salida adversa o error del moderador respeta el fail-closed (A2).
- [x] Logs solo con metadatos permitidos; ningún texto moderado aparece en logs.
- [x] `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE` presente en el payload, sin llamada
      extra y sin contenido en logs.
- [x] La plantilla de fallback no incluye el título ni el presupuesto (A6).
- [x] El contrato `{explanation, generated, promptVersion}` no cambia.
- [x] `ruff check .`, `mypy src` y `pytest` en verde, sin red.

## Seguridad

- [x] No registrar texto moderado ni motivos detallados con PII.
- [x] Minimizar datos enviados al moderador (moderador local: el texto no sale del proceso).
- [x] Limitar el tamaño del texto a moderar (900 caracteres).
- [x] Separar decisión de moderación de generación para poder auditarla.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `pytest` en verde y sin red.
- [x] Sin secretos, PII ni tokens en código, logs o fixtures.
- [x] Sin endpoints ni proveedores reales fuera de alcance.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.
