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

Tras el primer publish real se añadió `create-storage-record: false` a ambos pasos de
attestation: emitían el aviso `Failed to create storage record / artifact-metadata:write`.
No necesitamos esos metadatos, así que se deshabilita (mínimo privilegio). El test de
texto comprueba que aparece exactamente dos veces.

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

**Publish completo posterior (run CI #29):** imagen publicada con procedencia y SBOM
firmados (Sigstore/Rekor) y paquete GHCR público. Digest de la **imagen** a desplegar:

```text
ghcr.io/thehouse-team/thehouse-genai@sha256:8b5d250ce96cd338cab3ec2c0547e8c34704c1ec13c711ed019038d79e2b9edf
```

No confundir con `sha256:05659904...`, que es el digest de la **attestation**, no de la
imagen. El despliegue usará el digest de la imagen.

Digest publicado en el run #27 (no se usará para desplegar):
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

## Bloque B5 — Infraestructura (ajustes previos al commit)

Versiones de API verificadas en la referencia oficial de Microsoft Learn (ambas
existen y son estables, no preview): `Microsoft.App/containerApps@2025-01-01` y
`Microsoft.App/managedEnvironments@2025-01-01`. Fuentes:
`https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-01-01/containerapps`
y `https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-01-01/managedenvironments`.
No fue necesario cambiar las versiones del Bicep.

Decisiones documentadas en el runbook (Apéndice B de `spec.md`):

- **Rollback coherente con `activeRevisionsMode: Single`:** no se reactiva una revisión
  anterior; se redespliega el último digest bueno, creando una revisión nueva. B6 seguirá
  este enfoque. El historial de digests desplegados se registra en este `evidence.md` y en
  el resumen del job `publish`. Consulta del digest en ejecución:
  `az containerapp show --name ca-thehouse-genai-u2 --resource-group rg-thehouse-u2 --query properties.template.containers[0].image -o tsv`.
- **Reaplicación del Bicep:** siempre consultar primero ese digest y pasarlo a
  `--parameters imageDigest=...`; si se aplica otro digest se revierte la imagen sin aviso.
- **`GENAI_API_KEY` de producción:** debe venir de un proyecto de AI Studio separado
  (p. ej. `thehouse-genai-prod`), porque las cuotas de Gemini son por proyecto y no deben
  compartirse con el desarrollo local ni los smoke manuales.

## Actualización deliberada de pytest (hallazgo de pip-audit)

Hallazgo del paso no bloqueante `Dependency audit` en `Quality gates`:

```text
pytest 8.4.2  PYSEC-2026-1845  Fix Versions: 9.0.3
```

Verificación en la fuente oficial (`https://api.osv.dev/v1/vulns/PYSEC-2026-1845`):
`pytest has vulnerable tmpdir handling`, alias `CVE-2025-71176` / `GHSA-6w46-j5rx-g56g`.
Afecta a pytest hasta 9.0.2 en UNIX: el patrón de directorios
`/tmp/pytest-of-{user}` permite a usuarios locales causar denegación de servicio o
posible escalada de privilegios. En este repositorio pytest solo corre en el runner
efímero de GitHub (usuario único) y en la computadora local con Windows, así que el
escenario de explotación no aplica a nuestro uso; aun así se actualiza por higiene.

**No afecta a la imagen:** pytest es dependencia exclusiva de
`[project.optional-dependencies].dev`. No está en `requirements.lock` (lock de runtime)
y por tanto no se instala en el `Dockerfile`.

Relación con el PR #12 de Dependabot: proponía ampliar `pytest<9.0` a `<10` en
`pyproject.toml` sin regenerar los locks universales. Se cerró por ese motivo (el job
`lock-drift` lo haría fallar). Aquí se hace la misma ampliación de forma deliberada,
regenerando el lock con el comando de su cabecera:

```text
uv pip compile pyproject.toml --universal --generate-hashes --python-version 3.12 --extra dev -o requirements-dev.lock
```

- `pyproject.toml`: `pytest>=9.0.3,<10` (antes `>=8.3,<9.0`).
- `requirements-dev.lock`: `pytest==9.2.0`, con hashes.
- `requirements.lock` **no cambió**: SHA256 antes y después
  `7A87E3665482B93D019F3F81CF3E35B26EC1D364D50441CD7B39A1B675582B82`.
- `.venv` sincronizado con `pip install --require-hashes -r requirements-dev.lock` y
  `pip install --no-deps -e .`: `pytest 8.4.2` → `9.2.0`. No hicieron falta cambios de
  configuración, fixtures ni tests; los 1064 tests pasan y el único warning sigue siendo
  el conocido `StarletteDeprecationWarning` de `TestClient`.

`pip-audit==2.10.1` (versión obtenida de `https://pypi.org/pypi/pip-audit/json`)
ejecutado contra el entorno sincronizado:

```text
No known vulnerabilities found
Name           Skip Reason
-------------- -----------------------------------------------------------------------------
thehouse-genai Dependency not found on PyPI and could not be audited: thehouse-genai (0.1.0)
PIP_AUDIT_EXIT=0
```

El paquete se instaló temporalmente en el venv solo para la auditoría y se desinstaló
después: `ENV_RESTORED=identical_to_before` y `No broken requirements found`.

Fijación de `pip-audit` en el CI aplicada en el mismo cambio: el paso `Dependency audit`
usa ahora `python -m pip install "pip-audit==2.10.1"` (antes sin versión, lo que hacía el
gate no reproducible). Se actualizó `test_pip_audit_step_is_present_and_non_blocking`
para exigir la versión fijada. El step sigue siendo **no bloqueante**
(`continue-on-error: true`) y sigue siendo el único.

## Aplicación manual de la infraestructura por el operador (2026-11-19)

El operador aplicó la infraestructura desde Azure Cloud Shell; el CI no participó en esta
fase (D6). Hechos comunicados y registrados tal cual:

- `az deployment group what-if` con `infra/genai.bicep`: **1 create, 6 ignore**, sin cambios
  al Backend ni al entorno `cae-thehouse-u2`. No se creó ni modificó ningún recurso ajeno.
- Container App **`ca-thehouse-genai-u2`** creada con `infra/genai.bicep`.
  Revisión **`ca-thehouse-genai-u2--okuxih9`**: `Active`, `Healthy`,
  `RunningAtMaxScale` (1/1). Ingreso externo **`False`**. FQDN interno:
  `ca-thehouse-genai-u2.internal.grayisland-cb722b5f.eastus2.azurecontainerapps.io`
  (contiene el segmento `.internal.`).
- Imagen desplegada:
  `ghcr.io/thehouse-team/thehouse-genai@sha256:6411108f02043659bde838c1ae48362e3e9f5ed8ee33b59d08adc16939a9aa71`
  (CI **#31**, con procedencia y SBOM firmados). Este es el digest bueno conocido que debe
  usarse como entrada del workflow de rollback si una promoción posterior falla.
- Verificación puntual con `az containerapp exec` **dentro del contenedor de GenAI**, contra
  `localhost:8000`: `explain-match` **200** con `generated=true` (prompt `explain_match_v3`);
  `parse-search` **200** con `generated=true` y `confidence=high` (`maxBudget` 3000, `MXN`,
  `UTTT`, `internet`, `maxDistanceKm` 2); sin clave de servicio **401**. No se tocó el
  contenedor del Backend (D11).
- La clave de Gemini de producción está en un proyecto de AI Studio **separado**. Las claves
  de servicio y de métricas se generaron en Cloud Shell, se guardaron fuera del repositorio
  y se borraron de la sesión al terminar. No hay secretos versionados.
- **OIDC:** App Registration `thehouse-genai-gh-actions`; federated credential con subject
  `repo:thehouse-team/TheHouse-GenAI:environment:production`. Rol personalizado
  **`TheHouse GenAI Deployer`** con **solo 5 acciones**:
  `Microsoft.App/containerApps/read`, `Microsoft.App/containerApps/write`,
  `Microsoft.App/containerApps/revisions/read`,
  `Microsoft.App/containerApps/revisions/restart/action` y
  `Microsoft.App/containerApps/revisions/replicas/read`. No incluye
  `revisions/activate/action` ni `revisions/deactivate/action` (el modo es `Single` y el
  rollback es por redespliegue), ni `listSecrets` ni `delete`. Asignado **solo** sobre
  `ca-thehouse-genai-u2`. El runbook del Apéndice B de `spec.md` se actualizó para reflejar
  este conjunto exacto y el nuevo nombre del rol.
- Entorno **`production`** en GitHub con aprobación requerida, restringido a `main`, con
  variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
  `AZURE_RESOURCE_GROUP` y `AZURE_CONTAINER_APP` (no son secretos).
- El grupo vacío `thehouse-genai_group` del intento fallido de App Service se revisó
  (sin recursos) y se borró.

## Bloque B6 — Despliegue continuo con aprobación y rollback

### Acción fijada por SHA

| Acción | Versión | SHA del commit (40 hex) | Fuente |
| --- | --- | --- | --- |
| `azure/login` | v3.1.0 | `a641126d1b8aa4d1fa005f4f92df94a3a4c4c906` | `GET /repos/Azure/login/releases/latest` → tag `v3.1.0` (publicado 2026-09-10); `git/ref/tags/v3.1.0` → tag anotado `053f7285eb20bf5469ef084617b0b24d3cec53fc`; `git/tags/053f7285…` → commit `a641126d…`. Release: https://github.com/Azure/login/releases/tag/v3.1.0 |

Inputs confirmados en `action.yml@v3.1.0`: `client-id`, `tenant-id` y `subscription-id`
(audience OIDC por defecto `api://AzureADTokenExchange`). Ningún valor escrito de memoria.

### Job `deploy` en `ci.yml`

- Solo en `push` a `main`, `needs: publish`, `environment: production`,
  `permissions: contents: read` + `id-token: write` (exactamente dos). Sin checkout ni
  secretos: la autenticación es OIDC con las cinco variables del entorno protegido.
- Despliega `ghcr.io/thehouse-team/thehouse-genai@${DIGEST}` donde `DIGEST` es
  `needs.publish.outputs.digest`, validado antes contra `^sha256:[0-9a-f]{64}$`.
  Se usa `az containerapp update --image "$image"`, nunca un tag ni `:latest`.
- Antes de actualizar se lee la imagen activa con
  `az containerapp show --query properties.template.containers[0].image -o tsv` y se escribe
  en el resumen como **Previous image (for rollback)**.
- Verificación con 24 intentos y 10 s entre ellos (máximo ~4 min) sobre la revisión
  `latestRevisionName`: se obtiene la revisión con `az containerapp revision show ... -o json`
  y se valida con `.github/ci/revision_status.py` (detalle del primer fallo real y su
  corrección en la sección «Primer despliegue real»). Exige revisión activa,
  `provisioningState=Provisioned`, `runningState` no fallido e imagen **exactamente** el digest
  esperado; solo si `replicas >= 1` exige `healthState=Healthy`. Con 0 réplicas se acepta
  `runningState=ScaledToZero`/`Stopped` y `healthState=Healthy` o nulo. Falla inmediata ante estados de error o campos
  ausentes/vacíos. El resumen registra revisión, digest e imagen anterior; si falla el tiempo
  límite, el job termina en error **sin rollback automático**.

### Workflow `rollback.yml`

- `workflow_dispatch` con input obligatorio `image_digest`, validado contra
  `^ghcr\.io/thehouse-team/thehouse-genai@sha256:[0-9a-f]{64}$` antes de cualquier llamada
  a Azure.
- Mismo entorno protegido `production` (aprobación requerida), mismos permisos
  (`contents: read`, `id-token: write`) y misma acción `azure/login` fijada por SHA.
- Rechaza el rollback si el digest solicitado ya es la imagen activa; redespliega con
  `az containerapp update --image "$IMAGE_REF"` y aplica la misma verificación (activa,
  provisionada, no fallida, digest exacto y Healthy solo con réplicas). Coherente con
  `activeRevisionsMode: Single`: nunca activa una revisión antigua.

### Si el CLI pidiera permisos adicionales (no ampliados)

No se amplió el rol ni se usó Contributor. Si una ejecución real devuelve cualquiera de
estos errores, la acción faltante debe ser agregada **explícitamente** por el operador:

- `The client '...' does not have authorization to perform action
  'Microsoft.App/managedEnvironments/read' over scope
  '/subscriptions/<sub>/resourceGroups/rg-thehouse-u2/providers/Microsoft.App/managedEnvironments/cae-thehouse-u2'`.
  Acción requerida: `Microsoft.App/managedEnvironments/read` sobre ese entorno. Es la
  incidencia ya anticipada en D14; afectaría a `az containerapp update` y a
  `az containerapp show`.
- `... does not have authorization to perform action
  'Microsoft.App/containerApps/revisions/read' ...`. Acción ya incluida en el rol; si
  aparece, comprobar la propagación de la asignación y el `environment: production`
  correcto, no ampliar el rol.
- `... does not have authorization to perform action
  'Microsoft.App/containerApps/write' ...`. Acción ya incluida; comprobar que la
  asignación esté sobre `ca-thehouse-genai-u2` y no sobre otro recurso.

En ningún caso se concederán comodines `Microsoft.App/containerApps/*/action`,
`listSecrets`, permisos sobre `rg-thehouse-u2` ni el rol `Contributor`/`Container Apps
Contributor`.

### Mejora operativa de logging (cambio lógico separado, sin commit)

Los probes `/health/live` y `/health/ready` se ejecutan cada 5 s (≈17.000 líneas/día).
`RequestContextMiddleware` emite ahora `http.request.completed` en `DEBUG` solo cuando la
ruta empieza por `/health/` y el estado es **200**. Las respuestas no saludables de esas
mismas rutas y todas las demás rutas siguen en `INFO`, de modo que los errores no se
ocultan. Las métricas no cambian: los probes siguen contándose en `http_requests_total` y
en el histograma de latencia. `tests/test_health_access_logs.py` cubre ambos probes, una
ruta no health, un probe forzado a 500 y la continuidad de las métricas.

### Pruebas de texto nuevas

En `tests/test_ci_security.py`: deploy solo en `main` y `needs: publish`, entorno
`production`, permisos exactos, login OIDC fijado por SHA con las cinco variables,
despliegue por `@sha256` sin tag, espera/verificación de revisión, digest e imagen anterior,
workflow de rollback con validación de formato y entorno, y comprobación de que **todas**
las acciones de ambos workflows están fijadas por SHA de 40 hex.

### Salidas reales de los gates (2026-11-19)

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 36 source files

$ .venv\Scripts\python.exe -m pytest
1080 passed, 1 warning in 18.47s

$ .venv\Scripts\python.exe -c "import yaml,pathlib; ..."
.github/workflows/ci.yml OK ['quality', 'lock-drift', 'infra', 'image', 'publish', 'deploy']
.github/workflows/rollback.yml OK ['rollback']
```

El único warning es el conocido `StarletteDeprecationWarning` de `TestClient` con `httpx`
(deuda 008). Un fallo intermedio del nuevo test de logging (el ASGI mínimo no atendía
`lifespan` bajo `TestClient`) se corrigió implementando `lifespan.startup.complete` y
`lifespan.shutdown.complete`; los 5 tests del archivo pasan.

## Cambios de decisión del 2026-11-19 (acordados con el equipo, antes del commit)

Se registran aquí las cinco decisiones acordadas (D21–D25, también en `plan.md` y
`memoria.md`). El SHA de `azure/login` v3.1.0
`a641126d1b8aa4d1fa005f4f92df94a3a4c4c906` fue reconfirmado por el usuario.

### a) Política de costo $0: escalado a cero

- El operador aplicó el 2026-11-19 `az containerapp update --min-replicas 0` sobre
  `ca-thehouse-genai-u2`. Resultado observado: `minReplicas 0`, `maxReplicas 1`,
  `cooldownPeriod 300`, `pollingInterval 30`, `rules null` (antes de añadir la regla en Bicep).
- `infra/genai.bicep` queda con `minReplicas: 0`, `maxReplicas: 1`, `cooldownPeriod: 300`,
  `pollingInterval: 30` y una regla HTTP explícita:

  ```bicep
  rules: [
    {
      name: 'http-concurrency'
      http: {
        metadata: {
          concurrentRequests: '10'
        }
      }
    }
  ]
  ```

  Formato verificado en la referencia oficial de `Microsoft.App/containerApps@2025-01-01`
  (https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-01-01/containerapps)
  y en «Scaling in Azure Container Apps» (https://learn.microsoft.com/en-us/azure/container-apps/scale-app):
  la regla es `rules[].http.metadata.concurrentRequests`, con valor por defecto 10 (mínimo 1).
  Se elige **10** por ser el valor documentado por defecto y suficiente para el único cliente
  legítimo (Backend, timeout de 8 s). Con `maxReplicas=1`, el exceso se encola en el ingress.
- Consecuencias documentadas en el runbook (Apéndice B, sección 6b) del `spec.md`:
  **arranque en frío** cubierto por el fallback `generated=false` y el timeout de 6 s de
  GenAI frente a los 8 s del Backend; y **reinicio del estado en memoria** (presupuesto
  diario, rate limit y métricas) al escalar a 0, por lo que el tope local de 400 llamadas/día
  deja de ser exacto. El límite efectivo lo pone Gemini en capa gratuita: **500 RPD**
  (~15 RPM y 250K TPM por proyecto de AI Studio). Deuda 007-(a) queda agravada y documentada.
- Tests: `test_bicep_pins_scale_resources_and_probes` ahora exige `minReplicas: 0`,
  `cooldownPeriod: 300` y `pollingInterval: 30`; nuevo
  `test_bicep_has_one_explicit_http_scale_rule` comprueba una sola regla HTTP con
  `concurrentRequests: '10'`.

### b) Verificación tolerante a 0 réplicas en `deploy` y `rollback`

Con `minReplicas=0`, justo después de desplegar la revisión nueva puede estar en 0 réplicas y
`healthState` no ser `Healthy`. Se consultó la documentación oficial:

- Definiciones de la API REST de Container Apps (Get Revision): `RevisionProvisioningState` =
  `Provisioning | Provisioned | Failed | Deprovisioning | Deprovisioned`;
  `RevisionRunningState` = `Running | Processing | Stopped | Degraded | Failed | Unknown`;
  `RevisionHealthState` = `Healthy | Unhealthy | None`. Fuente:
  https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/container-apps-diagnostics/get-revision?view=rest-resource-manager-containerapps-2026-07-01
- Guía «Update and deploy changes in Azure Container Apps»: estados de ejecución
  «Scale to 0» (cero réplicas, sin aprovisionamiento en curso), «Activating», «Running»,
  «Running (at max)», «Degraded» y «Failed». Fuente:
  https://learn.microsoft.com/en-us/azure/container-apps/revisions

La verificación de ambos workflows exige ahora, en una sola consulta a la revisión:
`properties.active`, `properties.provisioningState == Provisioned`, `properties.runningState`
no fallido, `properties.template.containers[0].image` igual al digest esperado y, **solo si
`properties.replicas >= 1`**, `properties.healthState == Healthy`. Con 0 réplicas se acepta
`ScaledToZero`/`Stopped` con `healthState` `Healthy` o nulo. Falla inmediata si `provisioningState` es `Failed`/`Deprovisioning`/
`Deprovisioned`, `runningState` es `Failed`/`Degraded` o `healthState` es `Unhealthy`.
Ya no se exige `properties.state == Active` ni `replicas == 1`.

Tests actualizados: `test_deploy_waits_and_verifies_the_active_revision` y
`test_rollback_uses_the_same_verification` comprueban los nuevos campos y ausencia de
`"$replicas" == "1"`; `test_deploy_verification_accepts_scale_to_zero` verifica que no se
exige ni una réplica ni un estado `Active` antiguo.

### c) HTTPS interno verificado y `allowInsecure: false`

El 2026-11-19, desde dentro del entorno:
`https://ca-thehouse-genai-u2.internal.grayisland-cb722b5f.eastus2.azurecontainerapps.io/health/ready`
devolvió **200 con el payload exacto** y certificado válido. `infra/genai.bicep` cambia
`allowInsecure: true` → `false`; HTTP se redirige a HTTPS y **el Backend llamará a
`https://ca-thehouse-genai-u2`**. El runbook (paso 4) y la guía ya no recomiendan HTTP.
`test_bicep_references_existing_environment_and_internal_ingress` exige `false` y prohíbe `true`.

### d) Gemini permanece en capa gratuita

Por la política de costo $0 queda **derogada** la recomendación de crear un proyecto de pago
con tope de gasto (011/D-8 y deuda 004-(b)). En la capa gratuita Google puede usar el
contenido enviado para mejorar sus productos
(https://ai.google.dev/gemini-api/docs/billing); por eso GenAI aplica su redacción de PII
(spec 005) **antes de enviar** cualquier prompt. El proyecto de AI Studio de producción es
separado. El cupo local de 400 no es la garantía: la cuota real es de Gemini (500 RPD).

### e) Reaplicación en Azure y what-if previo

El runbook (Apéndice B, sección 6) indica ahora: consultar el digest en ejecución antes de
reaplicar; tomar los secretos del gestor de contraseñas del equipo con `read -rs` o archivo
temporal con `umask 077`; ejecutar `az deployment group what-if` con ese mismo digest y
revisarlo antes de `az deployment group create`. **Cambios esperados en el what-if: solo
`configuration.ingress.allowInsecure` (true → false) y `template.scale`** (minReplicas 1 → 0,
cooldownPeriod 300, pollingInterval 30, regla `http-concurrency`). No se espera ningún cambio
en secretos, variables, imagen ni en `cae-thehouse-u2`. Si aparece otro cambio, detener.
El cambio de ingress es de ámbito de aplicación (sin revisión nueva); el de `template.scale`
sí crea una revisión nueva.

### Gates tras estos cambios

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 36 source files

$ .venv\Scripts\python.exe -m pytest
1082 passed, 1 warning in 8.93s

$ git diff --check
(sin salida, código 0)
```

El único warning sigue siendo el `StarletteDeprecationWarning` heredado (deuda 008).

## Primer despliegue real del job `deploy` en `main` (2026-11-19)

### Login OIDC

El primer intento de `azure/login` falló por el `subject` de la federated credential: la
organización usa el formato con **IDs inmutables**, no el de nombres. Se creó la credencial
**`github-production-ids`** con
`repo:thehouse-team@350926140/TheHouse-GenAI@1450837796:environment:production` y se borró la
anterior. Con ese valor el login OIDC funcionó. El runbook del Apéndice B de `spec.md` ya
registra el formato real, los IDs y el nombre de la credencial. No se cambiaron permisos del
rol (`TheHouse GenAI Deployer` sigue con sus 5 acciones sobre la Container App).

### Fallo de la verificación y causa exacta

`az containerapp update` se ejecutó correctamente y creó la revisión
**`ca-thehouse-genai-u2--0000002`**. La verificación agotó los 24 intentos con este patrón:

```text
attempt 1/24: revision=ca-thehouse-genai-u2--0000002 active=true provisioning= running=
health= replicas=0 image=
...
Deployment verification failed after 24 attempts.
```

No era un fallo de la app ni de permisos: el `read` funcionó (`active=true`) y el despliegue
**sí funcionó**. El operador consultó después el estado real y la forma JSON de la revisión
(desglosados abajo), que confirman que la revisión estaba activa, provisionada, escalada a
cero y con la imagen correcta. La causa está en el **consumo de `-o tsv`**, no en las rutas
JMESPath. Azure CLI usa el formateador
`tsv` de `knack`:

- `format_tsv()` convierte el resultado de un query multi-select en una lista y llama a
  `_TsvOutput.dump()`.
- `dump()` itera la lista y `_dump_row()` escribe `'\\n'` **por cada elemento**.

Por tanto `--query '[a, b, c, ...]' -o tsv` imprime **una línea por campo**, no una fila
tabulada. El `IFS=$'\t' read -r active provisioning ... <<< "$row"` capturaba solo la primera
línea (`active=true`) y dejaba el resto vacío; `replicas` aparecía como 0 por el valor por
defecto del propio script. Fuentes verificadas:
https://github.com/microsoft/knack/blob/master/knack/output.py (`format_tsv`, líneas 84-87;
`_TsvOutput.dump`, 261-268; `_dump_row`, 232-258) y
https://github.com/Azure/azure-cli/blob/main/src/azure-cli/azure/cli/command_modules/containerapp/_clients.py
(`show_revision` devuelve el JSON ARM sin proyectar, línea 318 en adelante), además del
esquema REST de revisiones ya citado. Las rutas `properties.*` y
`properties.template.containers[0].image` son correctas; el fallo era exclusivamente la
lectura de la salida `tsv`.

### Estado real y forma JSON consultados por el operador (2026-11-19)

```text
Revision ca-thehouse-genai-u2--0000002 | Activa True | Aprov Provisioned |
Estado ScaledToZero | Salud Healthy | Replicas 0 |
Imagen ghcr.io/thehouse-team/thehouse-genai@sha256:bb106ef6ad5db6e460f88f7f004c7cfb4844034e8c1e5547a80366da60c64447
```

Segundo caso real observado el 2026-11-19 (revisión ya activa con 1 réplica):

```text
ca-thehouse-genai-u2--okuxih9  True  Healthy  RunningAtMaxScale  1
```

Forma real de `az containerapp revision show` (claves de primer nivel y de `properties`):

```text
raiz: ['id', 'name', 'properties', 'resourceGroup', 'type']
properties: ['active', 'createdTime', 'fqdn', 'healthState', 'provisioningState',
'replicas', 'runningState', 'template', 'trafficWeight']
```

La forma JSON coincide con el esquema ARM. Enumeraciones **exactas del swagger oficial**
`Microsoft.App/ContainerApps/stable/2025-01-01/ContainerAppsRevisions.json`
(https://github.com/Azure/azure-rest-api-specs/blob/main/specification/app/resource-manager/Microsoft.App/ContainerApps/stable/2025-01-01/ContainerAppsRevisions.json):

- `RevisionHealthState`: `Healthy`, `Unhealthy`, `None`.
- `RevisionProvisioningState`: `Provisioning`, `Provisioned`, `Failed`, `Deprovisioning`,
  `Deprovisioned`.
- `RevisionRunningState`: `Running`, `Processing`, `Stopped`, `Degraded`, `Failed`, `Unknown`.

El servicio emite además valores que el swagger no enumera, equivalentes a las etiquetas de
la guía «Update and deploy changes in Azure Container Apps»: **`ScaledToZero`** («Scale to
0», 0 réplicas) y **`RunningAtMaxScale`** («Running (at max)», 1 réplica), ambos observados
en producción. El parser los acepta como estados listos junto a `Stopped` y `Running`. Con
0 réplicas, `healthState` puede ser `Healthy` (caso real) o nulo; ambos son válidos.

Clasificación explícita implementada en `revision_status.py` (swagger citado + valores
reales de producción + etiquetas normalizadas de la guía oficial):

Criterio **vigente tras el tercer despliegue** (sección más abajo):

| Campo | LISTO (0) | ESPERAR (1) | FATAL (2) |
| --- | --- | --- | --- |
| `provisioningState` | `Provisioned` | `Provisioning`, vacío, desconocido | `Failed`, `Deprovisioning`, `Deprovisioned` |
| `runningState` (0 réplicas) | `ScaledToZero`, `Stopped` | vacío, desconocido, transitorios | `Failed`, `Degraded`, `ActivationFailed` |
| `runningState` (>=1 réplica) | `Running`, `RunningAtMaxScale` | `Processing`, `Activating`, vacío, desconocido | `Failed`, `Degraded`, `ActivationFailed` |
| `healthState` | `Healthy` (y `None` con 0 réplicas) | nulo/`None`/vacío con réplicas > 0, desconocido | `Unhealthy` |
| imagen | igual al digest esperado | distinta antes de `Provisioned` | distinta tras `Provisioned`, ausente o vacía |

Los valores vacíos y cualquier valor desconocido de los enums son una transición normal:
imprimen `WARNING: ...` con el valor (nunca secretos) y devuelven código 1.

### Corrección

- `ci.yml` y `rollback.yml` obtienen la revisión con
  `az containerapp revision show ... -o json > revision.json` (sin `--query` multi-select) y
  pasan el archivo a `.github/ci/revision_status.py --expected <digest>`.
- El parser (stdlib, sin red ni secretos) exige solo datos estructurales (`name`,
  `properties`, `template.containers[0].image` y un JSON válido). Todo lo demás se clasifica
  como listo, esperar o fatal según la tabla. Cada intento imprime una línea completa
  `revision=... active=... provisioning=... running=... health=... replicas=... image=...`,
  y al agotar los 24 intentos se imprime el último estado parseado.
- Códigos: `0` verificado, `1` aún no listo (reintenta con aviso), `2` fatal solo para fallo
  explícito documentado o dato estructural ausente/inválido.
- `tests/test_revision_status.py`: 28 tests sin red alimentan el parser con un JSON de ejemplo
  con la forma ARM real (sin secretos). Incluyen un test con **exactamente** el caso real
  (`Provisioned`, `ScaledToZero`, `Healthy`, 0 réplicas y el digest `bb106ef6…`) que devuelve
  código 0, parametrización de `healthState` `Healthy`/nulo, clasificación de los 12 valores
  de `runningState`, ambos casos reales y campos vacíos/inesperados. `tests/test_ci_security.py` comprueba que
  ambos workflows usan el parser, que no queda `IFS=` ni `--query '[` y que el código 2 aborta.
- `.github/ci/revision_status.py` está fuera de `src/`, que es lo que revisa `mypy src`, así
  que se añadió al job `quality` el paso bloqueante `mypy --strict .github/ci/revision_status.py`.
  No existe hoy un chequeo equivalente para `scripts/smoke_parse_search.py` en el CI.

### Gates tras la corrección

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 36 source files

$ .venv\Scripts\python.exe -m mypy --strict .github/ci/revision_status.py
Success: no issues found in 1 source file

$ .venv\Scripts\python.exe -m pytest
1115 passed, 1 warning in 11.60s

$ git diff --check
(sin salida, código 0)
```

## Segundo despliegue real: checkout faltante en `deploy` (2026-11-20)

El job `deploy` volvió a fallar en el intento 1/24 con:

```text
python3: can't open file '/home/runner/work/TheHouse-GenAI/TheHouse-GenAI/.github/ci/revision_status.py': [Errno 2] No such file or directory
Fatal revision state or invalid payload; aborting without rollback.
```

El mecanismo de **fallo fatal inmediato funcionó como se diseñó**: no se reintentó 24 veces,
se abortó en el primer intento con un mensaje claro. La causa es que los jobs `deploy` y
`rollback` no hacían checkout del repositorio, así que `.github/ci/revision_status.py` no
existía en el runner. No es un problema de permisos: `contents: read` ya cubre el checkout.

Corrección aplicada en `ci.yml` y `rollback.yml`:

- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` (el **mismo SHA
  verificado** que ya usan los demás jobs de `ci.yml`), antes de cualquier uso del parser,
  con `persist-credentials: false` para no dejar credenciales en el runner (la única auth
  del job es OIDC).
- En `deploy`, `ref: ${{ github.sha }}`: el job se dispara por `push` a `main`, así que se
  usa el commit exacto que disparó el despliegue y el parser corresponde al código desplegado.
- En `rollback`, se conserva el **ref por defecto del `workflow_dispatch`** (el ref que el
  operador selecciona al lanzar el workflow, normalmente `refs/heads/main`), sin `ref:`
  explícito. El rollback es una acción manual: el operador elige el ref desde el que se
  ejecuta y debe validarse con el parser de ese mismo ref. Fijar `github.sha` aquí sería
  incorrecto porque en un `workflow_dispatch` ese SHA no identifica el código con el que se
  quiere ejecutar la verificación.

Revisión del resto de jobs: `quality`, `lock-drift`, `infra` e `image` ya hacían checkout y
leen archivos del repo (locks, Bicep, Dockerfile). `publish` no hace checkout porque solo
descarga los artifacts `genai-image` y `sbom-spdx`; no lee archivos del repositorio. Tras
este cambio, todo job que ejecuta el parser tiene checkout previo.

Tests nuevos en `tests/test_ci_security.py`: comprueban, leyendo ambos YAML, que todo job
que ejecuta `.github/ci/revision_status.py` tiene un paso `actions/checkout` antes de ese
uso con `persist-credentials: false`; que `deploy` usa `ref: ${{ github.sha }}`; y que todos
los jobs que leen archivos del repo hacen checkout (con la excepción documentada de
`publish`). Con la versión anterior del workflow estos tests fallan porque no hay paso de
checkout en `deploy` ni en `rollback`.

## Tercer despliegue real: `healthState` nulo durante el arranque (2026-11-20)

Con el checkout ya corregido, la verificación abortó en el intento 1 con:

```text
FATAL: cannot parse revision JSON: healthState is null but replicas > 0: unexpected state
```

Justo después de `az containerapp update`, la revisión nueva tiene réplica pero Azure todavía
no ha evaluado su salud: `healthState` nulo con `replicas=1` es una **transición normal**, no
un fallo. Es el tercer estado real no previsto (después de `ScaledToZero` y
`RunningAtMaxScale`), así que se cambió el criterio del parser en lugar de añadir casos
aislados:

- **FATAL (2)** solo para fallo explícito documentado (`provisioningState`
  `Failed`/`Deprovisioning`/`Deprovisioned`, `runningState` `Failed`/`Degraded`/
  `ActivationFailed`, `healthState` `Unhealthy`) o datos estructurales ausentes/inválidos
  (sin `name`, sin imagen, JSON inválido, imagen distinta al digest esperado una vez
  aprovisionada).
- **ESPERAR (1)** para todo lo demás que aún no está listo: `healthState` nulo/`None` con
  réplicas > 0, valores vacíos y cualquier valor desconocido de los enums. Se imprime
  `WARNING: ...` con el valor, sin secretos.
- **LISTO (0)** solo con los estados válidos ya definidos y la imagen exacta.
- Cada intento imprime la línea completa del estado parseado; al agotar los intentos se
  imprime `Last parsed state: ...` con el último estado, en `ci.yml` y en `rollback.yml`.

Tests nuevos/ajustados en `tests/test_revision_status.py`: el caso real (réplicas 1 y
`healthState` nulo) da 1; un `runningState` desconocido da 1 con aviso; `Unhealthy` da 2;
imagen distinta al digest tras `Provisioned` da 2; los dos casos reales anteriores siguen
dando 0. `tests/test_ci_security.py` comprueba que ambos workflows imprimen el último estado.

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
- [x] SHA de cada acción con fecha y URL de su release oficial (B3); `azure/login` añadido
  en B6 con su tabla verificada más arriba.
- [x] Salidas de build, escaneo y SBOM en PR y en `main` (B3/B4).
- [x] Digest publicado en GHCR (CI #31) y revisión de ACA creada (B4/B5).
- [ ] Resultado del gating automático por revisión y probes (B6): implementado y cubierto
  por tests de texto; pendiente de su primera ejecución real en un push a `main`. La
  comprobación manual equivalente ya está registrada arriba (revisión `okuxih9`).
- [x] Verificación `exec` dentro de GenAI contra `localhost:8000` (B6).
- [ ] Revisiones antes y después del rollback probado (B6): workflow listo; pendiente de
  ejecutarse una vez con el digest `6411108f…` como entrada.
- [x] Resultados finales de los gates y `git diff --check` (B8).

## Evidencia requerida al cerrar

- [ ] Criterios de aceptación verificados (queda la prueba real del rollback y del gating
  automático en el primer push a `main`).
- [x] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Referencia al commit que cierra la spec: no se ha hecho commit (instrucción recibida).
- [ ] Solo entonces cambiar el estado a IMPLEMENTED.
