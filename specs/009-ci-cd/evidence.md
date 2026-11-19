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

## Bloque B1 — Contexto y lock (sin commit, según instrucción)

Hubo red disponible, por lo que no fue necesario pedir comando al usuario.

Instalación transitoria (no añade nada a `pyproject.toml`):

```text
.venv\Scripts\python.exe -m pip install --disable-pip-version-check "pip-tools==7.7.0"
Successfully installed build-1.6.1 pip-26.3 pip-tools-7.7.0 pyproject_hooks-1.3.3 setuptools-84.2.1 wheel-0.48.0
```

Generación del lock (el comando queda registrado en la cabecera del propio archivo):

```text
.venv\Scripts\python.exe -m piptools compile --generate-hashes --no-strip-extras --output-file requirements.lock pyproject.toml
```

- 23 distribuciones fijadas con `--hash=sha256:` (incluye transitivas y el extra
  `uvicorn[standard]`). No aparecen `mypy`, `pytest`, `ruff` ni `pip-tools`.
- `.dockerignore` implementado como lista blanca: `*`, `!src/`, `!src/**`,
  `!pyproject.toml`, `!requirements.lock`, `!README.md`, más exclusión de bytecode en
  `src/`.
- `tests/test_deployment_artifacts.py`: 5 tests sin red (cobertura de dependencias
  directas y extras, hashes por paquete, ausencia de paquetes de desarrollo, ausencia de
  `pip-tools` en `pyproject.toml` y whitelist del `.dockerignore`).

Salida real de los gates y comprobaciones finales:

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 36 source files

$ .venv\Scripts\python.exe -m pytest
1026 passed, 1 warning in 14.97s

$ git diff --check
(sin salida, codigo 0)

$ git status --short
 M specs/009-ci-cd/checklist.md
 M specs/009-ci-cd/evidence.md
 M specs/009-ci-cd/task.md
?? .dockerignore
?? requirements.lock
?? tests/test_deployment_artifacts.py

$ git log --oneline -3
5075696 docs: activate spec 009 with constitution amendment 1.2
6092cd5 feat: add natural language search (#8)
3128046 feat: add observability metrics and daily budget (#7)

$ git grep -n -P "[\x{4E00}-\x{9FFF}\x{3000}-\x{303F}\x{FF00}-\x{FFEF}]"
(sin salida, codigo 1 = cero coincidencias; PCRE verificado con un patron de control)
```

Nota: `specs/009-ci-cd/task.md`, `checklist.md` y este `evidence.md` también quedan
modificados en el árbol de trabajo al documentar B1; ninguno se ha confirmado.

### Validación en entorno limpio contra `requirements.lock` (2026-11-18)

Se creó un venv temporal **fuera del repositorio**, en
`C:\Users\cesar\AppData\Local\Temp\opencode\genai-lock-check`, y se eliminó al terminar
(`EXISTS_AFTER_DELETE=False`). Versiones instaladas desde el lock:

```text
fastapi 0.165.0
starlette 1.10.0
pydantic 2.14.3
pydantic-settings 2.16.3
httpx 0.28.1
uvicorn 0.54.0
```

Herramientas de desarrollo con las mismas versiones del venv local: `pytest 8.4.2`,
`mypy 1.20.2`, `ruff 0.17.5`. Instalación con `pip install --require-hashes -r
requirements.lock`, luego `pip install --no-deps -e .` y herramientas con `--no-deps`.

Gates en ese entorno:

```text
$ python -m ruff check .
All checks passed!

$ python -m mypy src
Success: no issues found in 36 source files

$ python -m pytest
1026 passed, 1 warning in 8.46s
```

Conclusión: las versiones nuevas del lock no rompen el código; no fue necesario acotar
dependencias en `pyproject.toml` ni corregir código.

**Incidencia intermedia `librt`:** el primer `pip check` informó
`mypy 1.20.2 requires librt, which is not installed`. Causa: las herramientas se
instalaron con `--no-deps` para no alterar las versiones fijadas por el lock. Se resolvió
instalando `librt==0.16.0` únicamente en el entorno temporal; después `pip check` devolvió
`No broken requirements found.` No afectó al repositorio ni a la imagen.

**Nota `StarletteDeprecationWarning` (deuda 008):** con starlette 1.10.0 el aviso es
idéntico al del venv local (`Using 'httpx' with 'starlette.testclient' is deprecated;
install 'httpx2' instead`), sigue siendo 1 warning y no se convierte en error. `TestClient`
funciona y los tests pasan. La deuda permanece igual; sin acción en G10.

### Lock de desarrollo y sincronización local

Comando registrado en la cabecera del propio archivo:

```text
pip-compile --extra=dev --generate-hashes --no-strip-extras --output-file=requirements-dev.lock pyproject.toml
```

`requirements-dev.lock` fija 34 distribuciones con hashes (runtime + herramientas y sus
transitivas: `ruff==0.17.5`, `mypy==1.20.2`, `pytest==8.4.2`, `librt==0.16.0`,
`pluggy==1.7.0`, `iniconfig==2.3.1`, `pygments==2.21.0`, `packaging==26.3`,
`mypy-extensions==1.2.0`, `pathspec==1.1.1`, `colorama==0.4.6`).

El `.venv` local no estaba alineado: tenía `fastapi==0.162.5`,
`pydantic-settings==2.16.2` y `annotated-doc==0.0.6`. Se sincronizó con
`pip install --require-hashes -r requirements-dev.lock` y
`pip install --no-deps -e .`, quedando en `fastapi==0.165.0`,
`pydantic-settings==2.16.3` y `annotated-doc==0.0.7`, igual que la imagen y el CI.

Cuatro tests de deriva nuevos en `tests/test_deployment_artifacts.py` (8 en total en ese
archivo): cobertura de dependencias directas en el lock de desarrollo, hashes en ambos
locks, igualdad de fijaciones runtime entre locks y separación de paquetes de desarrollo.

Gates finales de B1 con el `.venv` sincronizado:

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 36 source files

$ .venv\Scripts\python.exe -m pytest
1029 passed, 1 warning in 8.52s
```

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
