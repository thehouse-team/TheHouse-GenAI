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

- [ ] `.dockerignore` por whitelist: solo `src/`, `pyproject.toml`, `requirements.lock` y
      `README.md`.
- [ ] `requirements.lock` con hashes, generado con pip-tools transitorio, sin tocar
      `pyproject.toml`.
- [ ] Test de deriva entre las dependencias de ejecución de `pyproject.toml` y el lock.
- [ ] Gates en verde; mostrar salida real; no hacer commit ni avanzar a B2.

## B2 — Imagen

- [ ] `Dockerfile` multi-stage con `python:3.12-slim` fijado por digest verificado.
- [ ] Usuario no root, sin secretos, solo `src/` y lo necesario, `--no-server-header`.
- [ ] Sin `HEALTHCHECK` y con `EXPOSE 8000`.
- [ ] Tests de texto del Dockerfile y del `.dockerignore`.

## B3 — CI de imagen

- [ ] Job `image`: build sin publicar en PR, escaneo de vulnerabilidades y SBOM.
- [ ] Acciones fijadas por SHA verificado en release oficial (D3).
- [ ] Tests de texto del workflow: gates, `secrets.`, publicación y pinning.

## B4 — Publicación y CD

- [ ] Job `publish`: tag `sha-<SHA>`, digest en outputs, procedencia y SBOM.
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
