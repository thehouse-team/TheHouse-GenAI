# Checklist — 009-ci-cd CI/CD y despliegue

- **Estado:** ACTIVE (plan aprobado el 2026-11-18)

## Gobernanza

- [x] Enmienda 1.2 registrada en `constitution.md` y `memoria.md`.
- [x] `AGENTS.md` y `README.md` alineados con G10.
- [x] 009 ACTIVE en sus 5 archivos, con plan y decisiones D1–D14.
- [x] Alcance del rol OIDC documentado: solo `ca-thehouse-genai-u2`, con fuentes oficiales.

## Criterios de aceptación

- [ ] CI actual en verde y bloqueante.
- [ ] Imagen construida y probada en CI, sin asumir Docker local.
- [x] Digest de la imagen base verificado y registrado con fuente y fecha.
- [x] `.dockerignore` por whitelist y lock con hashes sin dependencias nuevas.
- [ ] PR construye y escanea sin publicar; `main` publica por SHA y digest con SBOM.
- [ ] Acciones fijadas por SHA de release oficial, sin valores de memoria.
- [ ] OIDC con rol personalizado de alcance único y sin `listSecrets`.
- [ ] Bicep aplicado manualmente; CI solo imagen y revisiones.
- [ ] Ingreso interno, una réplica, probes, secretos y variables verificados.
- [ ] Gating por revisión/probes y verificación `exec` documentada.
- [ ] Rollback por revisión probado y registrado.

## Seguridad

- [ ] Sin secretos, API keys, tokens ni PII en código, YAML, imagen, logs ni documentación.
- [ ] Sin acceso del CI a Log Analytics ni al contenedor del Backend.
- [ ] Sin ingress externo, aunque sea temporal.
- [ ] HSTS en el borde y `Server` suprimido por `--no-server-header`.
- [ ] Permisos mínimos y sin comodines `Microsoft.App/containerApps/*/action`.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] `git diff --check` limpio.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
