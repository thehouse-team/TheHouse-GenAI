# Tareas — 009-ci-cd CI/CD y despliegue

- **Estado:** IMPLEMENTED (plan aprobado el 2026-11-18; cerrado el 2026-11-22)

> Trabajo realizado en las ramas `feature/deployment`, `feature/deployment-cd` y
> `feature/close-ci-cd`, con los gates en verde antes de cada commit. Las decisiones D1–D27
> están en `plan.md` y en `memoria.md`.

## B0 — Gobernanza

- [x] Enmienda 1.2 en `constitution.md` (cabecera, artículos 9 y 10, tabla de enmiendas).
- [x] Enmienda 1.2 y activación de 009 en `memoria.md`.
- [x] `AGENTS.md` alineado con la spec activa y la excepción de Docker.
- [x] `README.md` con G10 en curso.
- [x] Los 5 archivos de `specs/009-ci-cd/` activados en B0 con plan y decisiones (hoy
      IMPLEMENTED).
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
- [x] Sin Docker local: la imagen se construyó y probó en CI; ver `evidence.md`.

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
- [x] Verificado en CI (run 44464597319: build, smoke y SBOM; escaneo corregido); ver `evidence.md`.

## B4 — Publicación y CD

- [x] Job `publish`: solo en `main`, tag `sha-<SHA>`, digest en outputs y resumen.
- [x] Attestation de procedencia y de SBOM ligadas al digest, con acciones oficiales
      fijadas por SHA verificado.
- [x] La imagen publicada es exactamente la que pasó smoke y escaneo (`docker save`/`load`).
- [x] Runbook: el paquete GHCR debe ser público y cómo verificarlo.
- [x] Mejora del smoke: línea `OK ...` por cada verificación.
- [x] Job `deploy` en `production` con OIDC y aprobación requerida.
- [x] Rol personalizado con alcance solo sobre `ca-thehouse-genai-u2` (D14).
- [x] Bicep de la Container App y del rol; aplicación manual por el usuario.

## B5 — Configuración ACA

- [x] Ingreso interno HTTPS, puerto 8000, 0.25 vCPU / 0.5 GiB, min=0 / max=1 con regla
      HTTP explícita de 10 concurrentes (política de costo $0, 2026-11-19).
- [x] Probes liveness, readiness y startup.
- [x] Secretos de ACA y variables de producción con D13.
- [x] Diagnostic settings a `log-thehouse-u2` y alertas sin acceso del CI a logs.

## B6 — Verificación y rollback

- [x] Gating por estado de revisión, réplicas y probes (job `deploy`, 24 intentos / 10 s).
- [x] Verificación controlada con `exec` dentro de GenAI contra `localhost:8000`, ejecutada
      por el operador (explain-match, parse-search y 401 sin clave).
- [x] Workflow y runbook de rollback redesplegando el último digest bueno (no reactivar una
      revisión: `activeRevisionsMode` es `Single`), con validación de formato y aprobación.
- [x] Prueba real del rollback (2026-11-22): `rollback.yml` con `sha256:47670b63…` (revisión
      `0000006`) y roll-forward con `sha256:a5e6051b…` (revisión `0000007`). Se planeó con
      `6411108f…`, pero se ejecutó con el digest bueno más reciente.
- [x] Mejora operativa: `http.request.completed` de `/health/*` con 200 bajado a DEBUG,
      errores y métricas conservados, con tests.

## B7 — Borde HTTP

- [x] `--no-server-header` verificado por test (smoke del contenedor y tests de texto).
- [x] HSTS documentado en el borde, sin cambios en los headers de la aplicación.

## B8 — Cierre

- [x] `checklist.md` y `evidence.md` con resultados reales.
- [x] Gates finales y sin secretos ni PII. No se hace commit ni PR (instrucción recibida);
      los cambios quedan en `feature/close-ci-cd`. Los PRs #9 y #13–#19 ya se integraron
      por squash a `main`.
- [x] Estado de los 5 archivos de 009 cambiado a IMPLEMENTED.
