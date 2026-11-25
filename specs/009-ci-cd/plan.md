# Plan — 009-ci-cd CI/CD y despliegue

- **Estado:** IMPLEMENTED (plan aprobado el 2026-11-18; cerrado el 2026-11-22)
- **Depende de:** 001, 002, 003, 004, 005, 006, 007, 008, 011
- **Rama:** `feature/deployment`

## Enfoque técnico

1. Conservar el workflow actual y sus tres gates sin cambios funcionales.
2. Un único `.github/workflows/ci.yml` con los jobs `quality`, `image`, `publish` y
   `deploy`; el digest de la imagen viaja por `needs` entre jobs.
3. La imagen se construye, escanea y prueba siempre en CI; no se asume Docker local.
4. La infraestructura se describe en Bicep y la aplica manualmente el usuario desde Azure
   Cloud Shell. El CI solo actualiza la imagen y gestiona revisiones de la Container App.
5. OIDC con federated credential del entorno `production` y rol personalizado asignado
   exclusivamente sobre `ca-thehouse-genai-u2`.
6. Despliegue por digest, verificación por estado de revisión y probes, y rollback por
   redespliegue del último digest bueno (`activeRevisionsMode` es `Single`).
7. Documentar promociones, rotación de claves y rollback antes de habilitar el CD.

## Decisiones aprobadas

| # | Decisión |
| --- | --- |
| D1 | Conservar la rama `feature/deployment` (ya creada y limpia). |
| D2 | Ratificar la enmienda 1.2 con el texto exacto acordado. |
| D3 | Fijar acciones por SHA solo de release oficial, verificado durante B3; sin acceso web, pedir el valor al usuario y nunca escribirlo de memoria. Igual para el digest de `python:3.12-slim` en B2. |
| D4 | Un único `ci.yml`: `quality`, `image`, `publish`, `deploy`. Sin `cd.yml` ni artifacts cruzados. |
| D5 | Solo el entorno protegido `production`; sin `staging`. |
| D6 | Bicep aplicado manualmente por el usuario en Cloud Shell; CI solo imagen y revisiones. |
| D7 | `ca-thehouse-genai-u2` en `cae-thehouse-u2`, `rg-thehouse-u2`, East US 2. |
| D8 | Originalmente `minReplicas=1`; **sustituido el 2026-11-19** por `minReplicas=0`, `maxReplicas=1` y regla HTTP explícita de 10 concurrentes por la política de costo $0. `maxReplicas=1`, 0.25 vCPU / 0.5 GiB se mantienen. |
| D9 | Secretos directos de ACA; sin Key Vault en esta spec. |
| D10 | Sin lectura de Log Analytics para el CI; gating por revisión y probes. |
| D11 | Verificación con `az containerapp exec` dentro del contenedor de GenAI contra `localhost:8000` con Python; no tocar el Backend. E2E de red en G09. |
| D12 | HSTS fuera de la app, documentado en el borde; `Server` suprimido con `--no-server-header`. |
| D13 | Capa gratuita, `gemini-3.5-flash-lite`, coste 0. **Se mantiene la capa gratuita** por la política de costo $0; queda derogada la recomendación de pasar a capa de pago. El límite efectivo es de Gemini (500 RPD), no el cupo local de 400, que deja de ser exacto al escalar a 0. |
| D14 | Alcance del rol OIDC **solo** sobre el recurso `ca-thehouse-genai-u2`, nunca sobre el grupo ni la suscripción, porque `rg-thehouse-u2` contiene el Backend. Rol personalizado sin `listSecrets`; no usar `Container Apps Contributor` por sus comodines `*/action`. Fuentes oficiales: permisos de Compute y "Manage secrets in Azure Container Apps" de Microsoft Learn. |
| D21 | Política de costo $0 del equipo: `minReplicas=0`, `maxReplicas=1`, regla HTTP explícita `concurrentRequests: '10'`, `cooldownPeriod: 300` y `pollingInterval: 30`. Formato verificado en la referencia de `Microsoft.App/containerApps@2025-01-01` y en «Scaling in Azure Container Apps». |
| D22 | El gating acepta 0 réplicas: exige revisión activa, `provisioningState=Provisioned`, `runningState` no fallido y digest exacto; `healthState=Healthy` solo si hay ≥1 réplica. Enums verificados en la API REST de revisiones y estados «Scale to 0»/«Failed»/«Degraded» de la guía oficial. |
| D23 | HTTPS interno verificado el 2026-11-19 con certificado válido y payload exacto; `allowInsecure: false` en el Bicep y Backend llamando a `https://ca-thehouse-genai-u2`. |
| D24 | Reaplicación del Bicep solo con el digest en ejecución, secretos del gestor de contraseñas y what-if previo; cambios esperados únicamente en `ingress.allowInsecure` y `template.scale`. |
| D25 | Gemini sigue en capa gratuita: en ese modo Google puede usar el contenido, por lo que se refuerza la redacción de PII antes del envío (spec 005). Quedan derogadas las recomendaciones de proyecto de pago de 011 y 004. |
| D26 | `az containerapp update` usa `-o none` en `deploy` y `rollback`: el log no debe contener el JSON completo de la app (IPs de salida, nombres de variables). Las consultas previas siguen siendo puntuales con `-o tsv`. |
| D27 | La verificación exige `trafficWeight=100` en la revisión nueva y ninguna otra revisión activa con tráfico, usando `az containerapp revision list -o json` leído de disco. Un peso parcial/ausente o una revisión ajena con tráfico es ESPERAR (1), nunca fatal (2), para no aprobar durante la transición. |

## Bloques de implementación

- **B0 — Gobernanza (docs).** Enmienda 1.2, activación de 009, AGENTS, README, decisión D14
  documentada con fuentes. Gates y commit `docs: activate spec 009 with constitution amendment 1.2`.
- **B1 — Contexto y lock.** `.dockerignore` por whitelist y `requirements.lock` con hashes
  generado con pip-tools transitorio; test de deriva contra `pyproject.toml`. Sin commit.
- **B2 — Imagen.** `Dockerfile` multi-stage, digest verificado, no root, `--no-server-header`,
  sin `HEALTHCHECK`, tests de texto.
- **B3 — CI de imagen.** Job `image` con build sin publicar en PR, escaneo, SBOM; acciones
  fijadas por SHA verificado; tests de texto del workflow.
- **B4 — Publicación y CD.** Job `publish` con tag de SHA y digest, job `deploy` en
  `production` con OIDC, rol personalizado y Bicep para infraestructura.
- **B5 — Configuración ACA.** Ingreso interno, puerto, réplicas, probes, secretos, variables,
  logs y alertas en Bicep; runbook de configuración.
- **B6 — Verificación y rollback.** Gating por revisión/probes, `exec` controlado, workflow
  y runbook de rollback por redespliegue del último digest bueno, prueba de rollback.
- **B7 — Borde HTTP.** Supresión de `Server` y documentación de HSTS; tests de headers.
- **B8 — Cierre.** Evidencia, checklist, memoria, PR con squash y squash en `main`.

## Archivos previstos

- `constitution.md`, `AGENTS.md`, `README.md`, `memoria.md`
- `specs/009-ci-cd/{spec,plan,task,checklist,evidence}.md`
- `.dockerignore`, `requirements.lock`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `infra/` (Bicep de la Container App y del rol personalizado)
- `tests/test_deployment_artifacts.py` y ampliación de `tests/test_ci_security.py`

## Estrategia de pruebas

- Sin red: los tests nuevos leen Dockerfile, `.dockerignore`, lock, YAML y Bicep como texto.
- El test de deriva compara las dependencias de ejecución de `pyproject.toml` con las
  entradas del lock, ignorando versiones y hashes.
- El test de CI comprueba que los tres gates siguen bloqueantes, que `pip-audit` sigue siendo
  informativo, que no aparece la cadena `secrets.`, que en PR no se publica y que todas las
  acciones están fijadas por SHA de 40 caracteres hexadecimales.
- Los tests existentes de headers, health y seguridad no se relajan.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Digest de la imagen base no verificable | Bloquea B2; se pide el valor al usuario, nunca se inventa. |
| SHA de acciones no verificable | Bloquea B3; se pide el valor al usuario, nunca se inventa. |
| Rol con alcance excesivo | Rol personalizado en el recurso; sin comodines ni `listSecrets`; verificación en Cloud Shell. |
| `managedEnvironments/read` exigido por la CLI | No ampliar el alcance; escalar al usuario. |
| Arranque en frío frente al timeout de 8 s (ahora esperado con `minReplicas=0`) | Fallback `generated=false` y timeout de 6 s en GenAI frente a 8 s en el Backend (D18 de 003). |
| Estado local multiplicado por réplicas | `maxReplicas=1`. |
| Rotación de secretos sin reinicio | Reiniciar la revisión activa en el runbook. |
| Exposición accidental | Ingreso interno permanente; sin ingress externo ni IP abierta. |
| Deriva de dependencias | Lock con hashes y test de deriva en CI. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src`, `pytest` y `git diff --check` en verde.
- Evidencia real con fuentes de los SHA y del digest, salidas de gates y prueba de rollback.
- Solo entonces se cambia el estado a IMPLEMENTED.
