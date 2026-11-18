# Tareas — 006-moderation Moderación de contenido

- **Estado:** ACTIVE
- **Alcance:** A (salida generativa + `safetySettings`)

## B1 — Activación y gobernanza

- [x] Activar 006 en `memoria.md` y en la cabecera de los 5 archivos de la spec.
- [x] Reescribir `plan.md` con los bloques B1–B6 y el alcance aprobado.
- [x] Reformular RF-02 y añadir `011-llm-provider` a las dependencias.
- [x] Registrar decisiones A1–A7 y el ajuste de la plantilla (A6).
- [x] Actualizar la descripción de la plantilla en la spec 003 sin cambiar el contrato.
- [x] Registrar la deuda (f) sobre la opción B en `memoria.md`.
- [x] Actualizar `README.md`.
- [x] Gates en verde y commit `docs: activate spec 006 moderation`.

## B2 — Política y detectores

- [ ] Crear `domain/moderation.py` con `POLICY_VERSION`, categorías y códigos de motivo.
- [ ] Detectores de correo, teléfono (10 dígitos, `+52` opcional) y URL (esquema o `www.`).
- [ ] Léxico ofensivo es-MX por palabra completa con allowlist de colisiones.
- [ ] Corpus benigno versionado en `tests/fixtures/moderation_benign_corpus.json`.
- [ ] Tests en `tests/test_moderation_policy.py`.

## B3 — Puerto y dobles

- [ ] DTOs, `ModerationProvider`, taxonomía de errores, guard, fake y moderador local.
- [ ] Tests en `tests/test_moderation_provider.py`.

## B4 — Integración en la salida

- [ ] Inyectar el puerto desde la capa HTTP y aplicar fail-closed (A2).
- [ ] Quitar el título de la plantilla de fallback (A6) y ajustar los tests afectados.
- [ ] Ampliar la allowlist de logs con decisión, categoría y versión.
- [ ] Tests en `tests/test_moderation_output.py`.

## B5 — safetySettings

- [ ] Añadir `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE` al payload de Gemini.
- [ ] Tests en `tests/test_gemini_safety.py` con `MockTransport`.

## B6 — Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a `IMPLEMENTED` solo al cumplir todo.
