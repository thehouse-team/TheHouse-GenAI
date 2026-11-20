# Checklist — 009-ci-cd CI/CD y despliegue

- **Estado:** ACTIVE (plan aprobado el 2026-11-18)

## Gobernanza

- [x] Enmienda 1.2 registrada en `constitution.md` y `memoria.md`.
- [x] `AGENTS.md` y `README.md` alineados con G10.
- [x] 009 ACTIVE en sus 5 archivos, con plan y decisiones D1–D14.
- [x] Alcance del rol OIDC documentado: solo `ca-thehouse-genai-u2`, con fuentes oficiales.

## Criterios de aceptación

- [x] Gates verdes localmente con el lock de desarrollo; workflow actualizado (ejecución en GitHub pendiente).
- [ ] Imagen construida y probada en CI, sin asumir Docker local (workflow listo; ejecución pendiente).
- [x] Digest de la imagen base verificado y registrado con fuente y fecha.
- [x] `.dockerignore` por whitelist y lock con hashes sin dependencias nuevas.
- [x] PR construye y escanea sin publicar; `main` publica por SHA y digest con SBOM.
- [x] Acciones fijadas por SHA de release oficial, sin valores de memoria.
- [x] Deriva de locks verificada en CI y Dependabot con tres ecosistemas y cooldown de 7 días.
- [x] OIDC con rol personalizado `TheHouse GenAI Deployer`, 5 acciones, alcance único y sin
      `listSecrets`, `delete` ni activate/deactivate.
- [x] Bicep aplicado manualmente por el operador; CI solo imagen y revisiones.
- [x] Ingreso interno HTTPS (allowInsecure false), escalado 0→1 con regla HTTP, probes,
      secretos y variables verificados.
- [x] Gating por revisión/probes implementado y verificación `exec` documentada y ejecutada.
- [ ] Rollback probado una vez con el digest bueno (workflow listo; prueba real pendiente).

## Seguridad

- [x] Sin secretos, API keys, tokens ni PII en código, YAML, imagen, logs ni documentación.
- [x] Sin acceso del CI a Log Analytics ni al contenedor del Backend.
- [x] Sin ingress externo, aunque sea temporal.
- [x] HSTS en el borde y `Server` suprimido por `--no-server-header`.
- [x] Permisos mínimos y sin comodines `Microsoft.App/containerApps/*/action`; posibles
      permisos adicionales documentados en `evidence.md` sin ampliar el rol.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `pytest` en verde y sin red (1080 tests).
- [x] `git diff --check` limpio.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED (falta la prueba real del rollback y
      del gating automático en el primer push a `main`).
