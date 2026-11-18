# Evidencia — 006-moderation Moderación de contenido

- **Estado:** ACTIVE
- **Fecha:** 2026-11-18
- **Alcance:** A (salida generativa + `safetySettings`)
- **Implementación:** B1 (documentación) completado; B2 en curso

## B1 — Activación y gobernanza

Spec activada el 2026-11-18 sobre la rama `feature/moderation`. Se reescribió `plan.md`
con los bloques B1–B6, se reformuló RF-02, se añadió `011-llm-provider` a las dependencias
y se registraron las decisiones A1–A7, incluido el ajuste de la plantilla de fallback
(A6: sin título de la propiedad). La spec 003 se actualizó solo en la descripción de la
plantilla; su contrato `{explanation, generated, promptVersion}` no cambia. La opción B
queda registrada como deuda (f) en `memoria.md` para una spec nueva.

### Gates

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 25 source files

$ .venv\Scripts\python.exe -m pytest
536 passed, 1 warning in 2.89s
```

El warning es el `StarletteDeprecationWarning` heredado de `TestClient` (deuda (e), 008).

- Commit: `docs: activate spec 006 moderation`.

## Evidencia requerida al cerrar

- [ ] Política `moderation_v1` aprobada, versionada y probada.
- [ ] Puerto, fake y moderador local probados sin red.
- [ ] Salida bloqueada no llega al usuario.
- [ ] Error del moderador respeta el fail-closed.
- [ ] Logs sin contenido sensible.
- [ ] Corpus benigno y léxico ofensivo probados.
- [ ] `safetySettings` verificado sin llamada extra.
- [ ] Plantilla de fallback sin título (A6) y contrato intacto.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
