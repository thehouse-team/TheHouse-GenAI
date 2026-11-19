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

## Bloque B2 — Dockerfile (sin commit, según instrucción)

Digest del índice multi-arquitectura de `python:3.12-slim` verificado en Docker Hub el
2026-11-18 y mostrado al usuario antes de escribir el archivo:
`sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`.
El campo `media_type` del tag es `application/vnd.oci.image.index.v1+json`; los digests
por arquitectura del array `images` no se usan.

Contenido final del `Dockerfile` (tras los ajustes de seguridad del usuario): dos etapas
(`builder`, `runtime`) sobre el mismo digest; el builder solo crea el venv en `/opt/venv`
e instala `requirements.lock` con `--require-hashes` (sin `pip install .`, sin setuptools
sin hash); el runtime copia `/opt/venv` desde el builder y `src` a `/app/src`, con
`PYTHONPATH=/app/src`. No hay `chown` ni `chmod`: todo lo copiado queda con dueño root y
modos por defecto 0644/0755, sin escritura para el usuario `10001`. Etapa runtime con
`USER 10001:10001`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `EXPOSE 8000`, sin
`HEALTHCHECK` y `CMD` de uvicorn con `--no-server-header` y `--workers 1`.

Tests de texto añadidos (18 en `tests/test_deployment_artifacts.py`): digest de 64 hex en
todos los `FROM`, multi-etapa, usuario no root, ausencia de chown/chmod hacia 10001,
`PYTHONPATH=/app/src`, `--require-hashes`, ausencia de `pip install .` y de setuptools,
`--no-server-header`, `--workers 1`, ausencia de COPY de `.env`/tests/specs/scripts,
ausencia de ARG/ENV con nombres de secretos, ausencia de HEALTHCHECK y presencia de
`EXPOSE 8000` y de los flags de Python.
No se ha construido la imagen: no hay Docker local; la construcción real se valida en B3.

## Bloque B3 — CI de imagen (sin commit, según instrucción)

Acciones fijadas por SHA. Versiones obtenidas de `GET /repos/{owner}/{repo}/releases/latest`
y SHA dereferenciado desde `GET /repos/{owner}/{repo}/git/ref/tags/{tag}` (objeto de tag
anotado cuando aplica). Consulta realizada el 2026-11-18. Ningún valor escrito de memoria.

| Acción | Versión | SHA | URL de la release |
| --- | --- | --- | --- |
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | https://github.com/actions/checkout/releases/tag/v7.0.1 |
| `actions/setup-python` | v7.1.0 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | https://github.com/actions/setup-python/releases/tag/v7.1.0 |
| `actions/upload-artifact` | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | https://github.com/actions/upload-artifact/releases/tag/v7.0.2 |
| `docker/setup-buildx-action` | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` | https://github.com/docker/setup-buildx-action/releases/tag/v4.4.1 |
| `docker/build-push-action` | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` | https://github.com/docker/build-push-action/releases/tag/v7.4.0 |
| `aquasecurity/trivy-action` | v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` | https://github.com/aquasecurity/trivy-action/releases/tag/v0.36.0 |

Inputs verificados en los `action.yml` de esos tags: `build-push-action` admite `push`,
`load`, `tags`, `context` y `file`; `trivy-action` admite `scan-type`, `image-ref`,
`exit-code`, `ignore-unfixed`, `severity`, `format`, `output` y `trivyignores`.

Otros cambios:

- `quality`: `pip install --require-hashes -r requirements-dev.lock` y
  `pip install --no-deps -e .`; Ruff, Mypy y Pytest siguen bloqueantes; `pip-audit` sigue
  informativo. El workflow no contiene la cadena `secrets.`.
- `lock-drift`: regenera ambos locks con `uv==0.13.9` (el mismo comando que la cabecera
  de cada lock, con `--universal --generate-hashes --python-version 3.12`) y ejecuta
  `git diff --exit-code -- requirements.lock requirements-dev.lock`.
- `image` (`needs: quality`): buildx con `push: false`, `load: true` y tag local
  `thehouse-genai:ci`; smoke con `GENAI_PROVIDER=fake` y `APP_ENV=production` que comprueba
  payload exacto de `/health/ready`, ausencia de header `Server`, `id -u` = 10001, 404 en
  `/docs` y `/openapi.json`, y escritura fallida en `/app/src` y `/opt/venv`; limpieza con
  `if: always()`. Escaneo Trivy bloqueante (`exit-code: "1"`, `HIGH,CRITICAL`,
  `ignore-unfixed: true`) con `.trivyignore` vacío y documentado; SBOM SPDX como artifact.
- `.github/dependabot.yml`: ecosistemas `docker`, `pip` y `github-actions` con
  `cooldown.default-days: 7` (clave verificada en la referencia oficial de Dependabot).
- Los tres jobs añadidos tienen `permissions: contents: read`.

Validación sintáctica local de ambos YAML con `yaml.safe_load`: correcta. La ejecución real
en GitHub (build, smoke, escaneo y SBOM) queda pendiente; no hay Docker local ni CI remoto
en esta sesión.

Fallos intermedios detectados y corregidos en B3 (primera ejecución de gates):

1. Ruff `E501` (104 > 100) en `tests/test_ci_security.py` al construir la lista de
   `uses:`. Se partió la comprensión de lista en varias líneas.
2. Dos tests heredados (`test_smoke_parse_search.py` y `test_smoke_script.py`) fallaron
   porque aseveraban `"smoke" not in ci.yml` para impedir que CI ejecutara los scripts
   manuales opt-in de 004 y 011. El smoke del contenedor de 009 introduce esa palabra
   legítimamente. Se estrechó la aserción a `"scripts/" not in workflow`, que es el
   contrato real (CI no invoca `scripts/smoke_*.py`) y sigue bloqueando cualquier intento
   de ejecutarlos. No se relajó ningún gate de calidad.

## Incidente PR #9 — locks dependientes de la plataforma (2026-11-18)

El CI del PR #9 falló en Linux: los locks se habían generado con `pip-compile` en Windows,
donde `uvicorn[standard]` no exige `uvloop`. El lock dejó `uvloop>=0.15.1` sin fijar, y
`pip install --require-hashes` en Linux abortó con:

```text
ERROR: In --require-hashes mode, all requirements must have their versions pinned with ==.
    uvloop>=0.15.1 ... (from uvicorn[standard]==0.54.0->-r requirements-dev.lock)
```

Fallaron `Quality gates` (no pudo instalar) y `Lockfile drift` (el lock regenerado en
Linux difería); `Image` quedó skipped. Lo mismo habría ocurrido con `colorama`, que solo
aplica en Windows.

Corrección: regenerar ambos locks como **universales** con `uv` fijado como herramienta
transitoria (versión `0.13.9`, obtenida de `https://pypi.org/pypi/uv/json`, no en
`pyproject.toml`). Comandos documentados en la cabecera de cada archivo:

```text
uv pip compile pyproject.toml --universal --generate-hashes --python-version 3.12 -o requirements.lock
uv pip compile pyproject.toml --universal --generate-hashes --python-version 3.12 --extra dev -o requirements-dev.lock
```

Líneas con marcadores verificadas (salida real):

```text
requirements.lock:438: uvloop==0.23.0 ; platform_python_implementation != 'PyPy' and sys_platform != 'cygwin' and sys_platform != 'win32' \
requirements-dev.lock:29: colorama==0.4.6 ; sys_platform == 'win32' \
requirements-dev.lock:676: uvloop==0.23.0 ; platform_python_implementation != 'PyPy' and sys_platform != 'cygwin' and sys_platform != 'win32' \
```

Verificación local en Windows (salida real):

```text
Ignoring uvloop: markers 'platform_python_implementation != "PyPy" and sys_platform != "cygwin" and sys_platform != "win32"' don't match your environment
Requirement already satisfied: colorama==0.4.6 in .\.venv\Lib\site-packages (from -r requirements-dev.lock (line 29)) (0.4.6)
```

Los 4 tests de deriva se ajustaron para comparar nombre, versión, extras **y marcador**
entre ambos locks, con un test adicional que exige los marcadores de `uvloop` y
`colorama` y las transitivas fijadas de `uvicorn[standard]` (uv universal aplana los
extras, así que `uvicorn` aparece sin `[standard]` y el test ya no exige el extra en la
línea del pin).

Hecho registrado el 2026-11-19: los bloques B0–B3 de esta spec entraron a `main` en el PR
#9 de forma anticipada, mediante un merge de un compañero sobre un borrador. La spec 009
sigue **ACTIVE**; G10 continúa en la rama `feature/deployment-cd`, creada desde `main`
actualizado.

## Primera ejecución real del job `image` (PR #9, run 44464597319)

Doble verificación: el **estado de cada step** se obtuvo de la API pública de GitHub
(`GET /repos/thehouse-team/TheHouse-GenAI/actions/jobs/135359463269`), y el **detalle del
smoke** de los logs reales copiados por el usuario. Los logs crudos no fueron descargables
desde esta sesión (la API responde `403 Must have admin rights to Repository` y la página
pública pide inicio de sesión), por lo que el detalle se registra tal cual fue facilitado:

Estados de los steps (API pública):

```text
4 | Build image without publishing | status=completed | conclusion=success | 05:22:20Z -> 05:22:39Z
5 | Container smoke               | status=completed | conclusion=success | 05:22:39Z -> 05:22:40Z
6 | Stop smoke container          | status=completed | conclusion=success | 05:22:40Z -> 05:22:41Z
7 | Vulnerability scan            | status=completed | conclusion=failure | 05:22:41Z -> 05:22:53Z
8 | Generate SBOM                 | status=completed | conclusion=skipped
9 | Upload SBOM                   | status=completed | conclusion=skipped
```

Por tanto el smoke **se ejecutó y pasó** (`success`, no `skipped`), y la limpieza del
contenedor también. Lo que falló fue únicamente el escaneo; al fallar ese step, SBOM y su
upload quedaron `skipped` y se ejecutarán cuando el escaneo pase. Los jobs `Quality gates`
y `Lockfile drift` de esa misma ejecución terminaron en `success`, confirmando la
corrección de los locks universales.

Detalle real del paso `Container smoke` (logs copiados por el usuario):

```text
Run set -euo pipefail
3ac531a98f726e0f91cba04aa76007adf712a19126d96fa3609bbad3b43a08c7
container smoke passed
```

`3ac531a98f726…` es el id del contenedor devuelto por `docker run -d`, y la última línea
es el `echo` propio del step. El script se ejecuta con `set -euo pipefail`, por lo que
cualquier comprobación fallida (payload de `/health/ready`, ausencia de header `Server`,
`id -u` distinto de `10001`, `/docs` o `/openapi.json` que no den `404`, o escritura
permitida en `/app/src` o `/opt/venv`) habría terminado el step antes de imprimir
`container smoke passed`. Junto con `conclusion=success` de la API, confirma que todas las
verificaciones del smoke se ejecutaron y pasaron, y no fueron saltadas.

Resultado del escaneo Trivy (reportado por el usuario):

```text
zlib1g  CVE-2026-85091  HIGH  fixed
  instalada: 1:1.3.dfsg+really1.3.1-1+b1
  corregida: 1:1.3.dfsg+really1.3.1-1+deb13u1
  desbordamiento de buffer de montón en gz_vacate
Todas las dependencias de Python: 0 vulnerabilidades
```

Decisión: **no añadir nada a `.trivyignore`**. Existe parche disponible, así que se aplica
el paquete corregido en la etapa runtime con versión exacta (ver `Dockerfile`). No se
acepta una excepción para una vulnerabilidad corregible.

Comprobación previa al parche (2026-11-18): `GET
https://hub.docker.com/v2/repositories/library/python/tags/3.12-slim` sigue devolviendo el
mismo digest `sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`
con `last_updated` `2026-11-08T05:06:56Z`; no hay digest más reciente que ya incluya el
paquete corregido, por lo que se aplica el paso 2. El parche lleva un comentario para
retirarlo cuando el digest base lo incluya (Dependabot propondrá el nuevo digest).

## Bloque B4 — Publicación en GHCR (sin commit, según instrucción)

Acciones nuevas fijadas por SHA verificado en la API oficial de GitHub (tag dereferenciado;
ningún valor escrito de memoria):

| Acción | Versión | SHA | URL de la release |
| --- | --- | --- | --- |
| `actions/attest-build-provenance` | v4.2.2 | `4d101475d8b20a2381f78447822ac1eab6504dd8` | https://github.com/actions/attest-build-provenance/releases/tag/v4.2.2 |
| `actions/attest` | v4.2.2 | `1e69f48acb82d1966a394da916b4c1698aa569d6` | https://github.com/actions/attest/releases/tag/v4.2.2 |
| `actions/download-artifact` | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` | https://github.com/actions/download-artifact/releases/tag/v8.0.2 |

`actions/attest-sbom` no se usa: su propio `action.yml` en v4.1.0 emite el aviso
`actions/attest-sbom has been deprecated, please use actions/attest instead`. El SBOM se
atesta con `actions/attest` mediante `sbom-path`.

Garantía de que se publica la imagen probada: el job `image` construye **una sola vez**
con `build-push-action` (`push: false`, `load: true`, tag local `thehouse-genai:ci`); el
smoke y Trivy se ejecutan contra **ese mismo tag local**. Si todo pasa y el evento es
`push` a `main`, ese step hace `docker save thehouse-genai:ci -o image.tar` y lo sube como
artifact `genai-image`. El job `publish` no vuelve a construir: descarga ese artifact,
hace `docker load -i image.tar`, y solo aplica `docker tag` + `docker push` con el tag
inmutable `sha-<SHA completo>`. El `docker push` devuelve el digest, que se usa como
`subject-digest` de ambas attestation y se escribe en el resumen del job. No hay
`build-push-action` en el job `publish`.

Permisos del job `publish`: `contents: read`, `packages: write`, `id-token: write`,
`attestations: write`. Login en `ghcr.io` con `${{ github.token }}` mediante
`--password-stdin`; el workflow no contiene la cadena `secrets.` ni `:latest`.

Mejora del smoke aplicada: cada verificación emite su propia línea `OK ...` (payload,
sin `Server`, uid 10001, `/docs`, `/openapi.json`, y escritura denegada en `/app/src` y
`/opt/venv`), seguida de `container smoke passed`.

## Primera tanda de PRs de Dependabot (#10, #11, #12)

Tras el merge del PR #9, Dependabot abrió tres PRs que se cierran:

| PR | Ecosistema | Propuesta | Motivo del cierre |
| --- | --- | --- | --- |
| #10 | docker | `python:3.12-slim` → `python:3.15-slim` | Cambia la versión mayor de Python; el CI falló. El servicio está fijado a 3.12 (constitución y `requires-python >=3.12`), y el salto de runtime queda fuera de G10. Se quiere seguir recibiendo nuevos digests y parches de 3.12-slim. |
| #11 | pip | `mypy <2.0` → `<3.0` en `pyproject.toml` | Amplía a una versión mayor y no regenera los locks universales. |
| #12 | pip | `pytest <9.0` → `<10.0` en `pyproject.toml` | Igual que #11: salto de versión mayor sin regenerar los locks. |

Ajuste aplicado en `.github/dependabot.yml` en esta rama:

- `docker`: `ignore` con `dependency-name: "python"` para
  `version-update:semver-major` y `version-update:semver-minor`. Siguen llegando nuevos
  digests y parches de 3.12-slim.
- `pip`: `ignore` con `dependency-name: "*"` para `version-update:semver-major`, más un
  comentario que documenta que Dependabot no regenera `requirements.lock` ni
  `requirements-dev.lock`; cada PR de pip debe regenerarlos con el comando `uv` de la
  cabecera de cada lock antes de mergearse, y el job `lock-drift` lo hará fallar si no.
- `github-actions`: sin cambios; actualizar acciones fijadas por SHA es deseable.
- `cooldown.default-days: 7` se mantiene en los tres ecosistemas.

Validación local: `yaml.safe_load` correcto y nuevos tests de texto que comprueban los
`ignore` de docker y pip, el comentario de regeneración y el cooldown en los tres
ecosistemas.

## Primer publish real en `main` (run CI #27)

Resultado: la imagen se publicó y la attestation de procedencia se firmó
correctamente, pero falló `Attest SBOM`:

```text
Run actions/attest@1e69f48... with:
  subject-name: ghcr.io/thehouse-team/thehouse-genai@sha256:782fd3af...
  sbom-path: sbom.spdx.json
Error: One of subject-path, subject-digest, or subject-checksums must be provided
```

Digest publicado en ese run:
`sha256:782fd3afce2aadddf66b273158f5abf73600bc612641dddad23ed56dd9a1f5b0`.
Estado: publicado con procedencia, **sin attestation de SBOM**. Causa: el paso
`Attest SBOM` pasaba el digest dentro de `subject-name` (`...genai@sha256:...`) y no
proporcionaba `subject-digest`; la acción `actions/attest` exige uno de
`subject-path`, `subject-digest` o `subject-checksums`. El paso de procedencia sí usaba
el esquema correcto (`subject-name` sin digest + `subject-digest` con el digest del push).

Corrección aplicada en `ci.yml`: `Attest SBOM` usa ahora
`subject-name: ghcr.io/thehouse-team/thehouse-genai` y
`subject-digest: ${{ steps.push.outputs.digest }}`, idéntico al paso de procedencia.
Nuevo test de texto: ambos pasos de attestation declaran `subject-digest` y ningún
`subject-name` contiene `@`.

**Este digest no se usará para desplegar.** El despliegue (B5) utilizará el digest del
próximo publish en el que ambas attestations terminen en verde.

## Bloques B2–B8

- [x] Digest de `python:3.12-slim` con fecha y URL de la fuente oficial (B2):
  `sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`, obtenido
  el 2026-11-18 de `https://hub.docker.com/v2/repositories/library/python/tags/3.12-slim`
  (`media_type: application/vnd.oci.image.index.v1+json`, es decir índice multi-arquitectura;
  `last_updated` de la fuente `2026-11-08T05:06:56Z`).
  **Verificado manualmente por el usuario el 2026-11-18** contra esa misma URL: el campo
  `digest` de nivel principal coincide exactamente con el del `Dockerfile`.
- [x] Verificación previa al cambio de B2: no existe uso de `importlib.metadata`,
  `importlib.resources`, `pkg_resources` ni `get_distribution` en `src/`; la versión es la
  constante `__version__` de `thehouse_genai/__init__.py`. El archivo de datos de
  moderación se resuelve desde el árbol `src/` mediante `Path(__file__).with_name(...)`,
  por lo que funciona con `PYTHONPATH=/app/src`. No se abrió ni citó su contenido.
  Nada depende de que el paquete esté instalado.
- [ ] Se muestran solo los tests de texto del Dockerfile; la construcción real se valida
  en CI en B3.
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
