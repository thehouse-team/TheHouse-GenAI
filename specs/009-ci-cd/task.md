# Tareas — 009-ci-cd CI/CD y despliegue

- **Estado:** ACTIVE (plan aprobado el 2026-11-18)

> Trabajar solo en las tareas de este archivo, en la rama `feature/deployment`, y con los
> gates en verde antes de cada commit. Las decisiones D1–D14 están en `plan.md`.

## B0 — Gobernanza

- [x] Enmienda 1.2 en `constitution.md` (cabecera, artículos 9 y 10, tabla de enmiendas).
- [x] Enmienda 1.2 y activación de 009 en `memoria.md`.
- [x] `AGENTS.md` alineado con la spec activa y la excepción de Docker.
- [x] `README.md` con G10 en curso.
- [x] Los 5 archivos de `specs/009-ci-cd/` en estado ACTIVE con plan y decisiones.
- [x] Decisión D14 documentada con fuentes oficiales de Microsoft Learn.
- [x] Gates en verde y commit `docs: activate spec 009 with constitution amendment 1.2`.

## B1 — Contexto y lock (sin commit)

- [x] `.dockerignore` por whitelist: solo `src/`, `pyproject.toml`, `requirements.lock` y
      `README.md`.
- [x] `requirements.lock` con hashes, generado con pip-tools transitorio, sin tocar
      `pyproject.toml`.
- [x] Test de deriva entre las dependencias de ejecución de `pyproject.toml` y el lock.
- [x] Gates en verde; salida real registrada en `evidence.md`; sin commit y sin avanzar a B2.

## B2 — Imagen

- [x] `Dockerfile` multi-stage con `python:3.12-slim` fijado por digest verificado.
- [x] Usuario no root, sin secretos, solo `src/` y lo necesario, `--no-server-header`.
- [x] Sin `HEALTHCHECK` y con `EXPOSE 8000`.
- [x] Tests de texto del Dockerfile y del `.dockerignore`.
- [ ] Sin commit y sin avanzar a B3 (según instrucción).

## B3 — CI de imagen

- [x] Job `quality` instala desde `requirements-dev.lock` con `--require-hashes` y luego
      `pip install --no-deps -e .`; gates bloqueantes sin cambios.
- [x] Job `lock-drift` regenera ambos locks con `uv==0.13.9` universal y falla con `git diff`
      (corrección del incidente del PR #9).
- [x] Job `image` con buildx (`push: false`, `load: true`) en PR y en `main`.
- [x] Smoke del contenedor: payload exacto, sin header `Server`, uid 10001, docs 404 y
      escritura denegada en `/app/src` y `/opt/venv`; limpieza con `if: always()`.
- [x] Escaneo Trivy bloqueante en HIGH/CRITICAL con `.trivyignore` vacío documentado.
- [x] SBOM SPDX como artifact.
- [x] `.github/dependabot.yml` con docker, pip y github-actions y cooldown de 7 días.
- [x] Todas las acciones fijadas por SHA de 40 hex verificado en release oficial.
- [x] Tests de texto del workflow, dependabot y permisos mínimos.
- [ ] Sin commit y sin avanzar a B4 (según instrucción).

## B4 — Publicación y CD

- [x] Job `publish`: solo en `main`, tag `sha-<SHA>`, digest en outputs y resumen.
- [x] Attestation de procedencia y de SBOM ligadas al digest, con acciones oficiales
      fijadas por SHA verificado.
- [x] La imagen publicada es exactamente la que pasó smoke y escaneo (`docker save`/`load`).
- [x] Runbook: el paquete GHCR debe ser público y cómo verificarlo.
- [x] Mejora del smoke: línea `OK ...` por cada verificación.
- [ ] Job `deploy` en `production` con OIDC y aprobación requerida.
- [ ] Rol personalizado con alcance solo sobre `ca-thehouse-genai-u2` (D14).
- [ ] Bicep de la Container App y del rol; aplicación manual por el usuario.

## B5 — Configuración ACA

- [ ] Ingreso interno, puerto 8000, 0.25 vCPU / 0.5 GiB, min=max=1.
- [ ] Probes liveness, readiness y startup.
- [ ] Secretos de ACA y variables de producción con D13.
- [ ] Diagnostic settings a `log-thehouse-u2` y alertas sin acceso del CI a logs.

## B6 — Verificación y rollback

- [ ] Gating por estado de revisión, réplicas y probes.
- [ ] Verificación controlada con `exec` dentro de GenAI contra `localhost:8000`.
- [ ] Job y runbook de rollback por revisión anterior, con prueba registrada.

## B7 — Borde HTTP

- [ ] `--no-server-header` verificado por test.
- [ ] HSTS documentado en el borde, sin cambios en los headers de la aplicación.

## B8 — Cierre

- [ ] `checklist.md` y `evidence.md` con resultados reales.
- [ ] Gates finales, sin secretos ni PII, PR con squash a `main`.
- [ ] Cambiar estado a IMPLEMENTED solo al cumplir todo.
