# Evidencia — 009-ci-cd CI/CD y despliegue

- **Estado:** ACTIVE (plan aprobado el 2026-11-18)
- **Fecha:** 2026-11-18
- **Implementación:** en curso (B0 completado, B1 en ejecución)

## Bloque B0 — Gobernanza

Evidencia a registrar con el commit de gobernanza:

- Salida real de `ruff check .`, `mypy src`, `pytest` y `git diff --check`.
- Hash del commit `docs: activate spec 009 with constitution amendment 1.2`.
- Fuentes consultadas para la decisión D14:
  - `https://learn.microsoft.com/en-us/azure/role-based-access-control/permissions/compute`
  - `https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets`
  - `https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/containers`

## Bloque B1 — Contexto y lock

- [ ] Comando exacto usado para generar `requirements.lock` y versión de pip-tools.
- [ ] Lista de paquetes fijados con hashes y salida del test de deriva.
- [ ] Si la generación requirió red y no estuvo disponible, comando entregado al usuario.

## Bloques B2–B8

- [ ] Digest de `python:3.12-slim` con fecha y URL de la fuente oficial (B2).
- [ ] SHA de cada acción con fecha y URL de su release oficial (B3).
- [ ] Salidas de build, escaneo y SBOM en PR y en `main` (B3/B4).
- [ ] Digest publicado en GHCR y revisión de ACA creada (B4/B5).
- [ ] Resultado del gating por revisión y probes (B6).
- [ ] Verificación `exec` dentro de GenAI contra `localhost:8000` (B6).
- [ ] Revisiones antes y después del rollback probado (B6).
- [ ] Resultados finales de los gates y `git diff --check` (B8).

## Evidencia requerida al cerrar

- [ ] Criterios de aceptación verificados.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Referencia al commit que cierra la spec.
- [ ] Solo entonces cambiar el estado a IMPLEMENTED.
