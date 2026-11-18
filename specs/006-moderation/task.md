# Tareas — 006-moderation Moderación de contenido

- **Estado:** IMPLEMENTED
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

- [x] Crear `domain/moderation.py` con `POLICY_VERSION`, categorías y códigos de motivo.
- [x] Detectores de correo, teléfono (10 dígitos, `+52` opcional) y URL (esquema o `www.`).
- [x] Léxico ofensivo cargado desde un archivo de datos, por palabra completa, con
      allowlist de colisiones y términos ficticios en tests.
- [x] Corpus benigno versionado en `tests/fixtures/moderation_benign_corpus.json`.
- [x] Tests en `tests/test_moderation_policy.py`.

## B3 — Puerto y dobles

- [x] DTOs, `ModerationProvider`, taxonomía de errores, guard, fake y moderador local.
- [x] Tests en `tests/test_moderation_provider.py`.

## B4 — Integración en la salida

- [x] Inyectar el puerto desde la capa HTTP y aplicar fail-closed (A2).
- [x] Quitar el título y el presupuesto de la plantilla de fallback (A6).
- [x] Ampliar la allowlist de logs con decisión, categoría y versión.
- [x] Tests en `tests/test_moderation_output.py` y ajuste de los tests de 003.

## B5 — safetySettings

- [x] Añadir `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE` al payload de Gemini.
- [x] Tests en `tests/test_gemini_safety.py` con `MockTransport`.

## B6 — Cierre

- [x] Política `moderation_v1` escrita en `spec.md` con responsable y ruta de ampliación.
- [x] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [x] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [x] Revisar seguridad y ausencia de secretos/PII.
- [x] Actualizar `memoria.md` y `README.md`.
- [x] Cambiar el estado a `IMPLEMENTED` al cumplir todo.
