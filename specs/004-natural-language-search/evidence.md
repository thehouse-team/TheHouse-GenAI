# Evidencia — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** ACTIVE
- **Fecha:** 2026-11-18
- **Implementación:** en curso sobre la rama `feature/natural-language-search`

## Resultado parcial

B0 completado: spec activada, contrato final acordado con Backend (incluye
`maxDistanceKm` y `promptVersion`), decisiones D1–D13 y ajustes obligatorios
registrados, dependencias ampliadas y `AGENTS.md`/`README.md` alineados. Sin código de
producción todavía; la evidencia de gates y tests se registrará al cierre de la spec.

## Evidencia requerida al cerrar

- [ ] Resultado real de `ruff check .`, `mypy src` y `pytest` sin red.
- [ ] Corpus versionado y pruebas del contrato, inyección, PII y moderación.
- [ ] Prueba manual opt-in con Gemini real registrada (sin credenciales ni PII).
- [ ] Revisión de seguridad y confirmación de ausencia de secretos y caracteres CJK.
- [ ] Referencia al commit que cierra la spec.
