# Checklist — 009-ci-cd CI/CD

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] CI actual se mantiene en verde y bloqueante.
- [ ] Escaneos integrados sin filtrar secretos.
- [ ] Artefacto y SBOM generados.
- [ ] Staging con aprobación manual.
- [ ] Rollback documentado y probado.
- [ ] Protección de rama activa.

## Seguridad

- [ ] Secretos solo en el gestor de CI, nunca en logs.
- [ ] Acciones de terceros fijadas por versión/commit.
- [ ] Permisos mínimos (`contents: read` por defecto).
- [ ] Artefacto firmado o verificable cuando aplique.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
