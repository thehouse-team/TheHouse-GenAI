# 009-ci-cd — CI/CD y despliegue

- **Estado:** ACTIVE (plan aprobado el 2026-11-18)
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  004-natural-language-search, 005-security, 006-moderation, 007-observability, 008-testing,
  011-llm-provider
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08
- **Rama:** `feature/deployment`

## Objetivo

Evolucionar el pipeline bloqueante actual hacia entrega segura: imagen reproducible y
endurecida, escaneos, SBOM, publicación en GHCR y despliegue por digest en Azure Container
Apps con OIDC, entorno protegido y rollback por revisiones.

## Contexto

La suscripción de prueba de Azure (créditos hasta el 2026-12-02) tiene cuota 0 para App
Service, por lo que esa vía no es viable antes de la entrega. El Backend ya corre en Azure
Container Apps: app `ca-thehouse-u2`, entorno `cae-thehouse-u2` (perfiles de carga de
trabajo), grupo `rg-thehouse-u2`, región East US 2 y workspace `log-thehouse-u2`. No existe
Azure Container Registry; la imagen del Backend es pública en GHCR y se referencia por
digest. La enmienda 1.2 de la constitución autoriza un `Dockerfile` y un `.dockerignore`
exclusivamente para la imagen de despliegue de GenAI, sin `docker-compose` ni dependencias
nuevas en `pyproject.toml`.

La computadora de desarrollo puede no tener Docker: la imagen se construye y se prueba en
CI. Ningún bloque de esta spec asume ejecución local de Docker.

## Alcance

### Incluido

- Mantener los gates actuales como obligatorios y bloqueantes.
- `.dockerignore` estricto por whitelist y `Dockerfile` multi-stage con imagen base fijada
  por digest verificado, usuario no root, dependencias con hashes y sin secretos.
- Escaneo de secretos y dependencias, build de imagen en PR sin publicar, escaneo de la
  imagen y generación de SBOM.
- Publicación en `ghcr.io/thehouse-team/thehouse-genai` con tag del SHA completo y
  attestations ligadas al digest.
- CD a `ca-thehouse-genai-u2` por digest, con OIDC y entorno `production` protegido.
- Configuración de la Container App: ingreso interno, puerto 8000, una réplica, probes,
  secretos de ACA, variables de producción y logs a `log-thehouse-u2`, definida en Bicep
  y aplicada manualmente por el usuario desde Azure Cloud Shell.
- Rol personalizado con permisos mínimos y alcance exclusivo sobre la Container App.
- Verificación por estado de revisión y probes, ejecución controlada por `exec`, rollback
  documentado y probado, y protección de rama.

### Excluido

- Exponer GenAI a internet o crear un ingress externo, aunque sea temporal.
- Dar al CI lectura de Log Analytics: el workspace contiene también los logs del Backend.
- Tocar, reiniciar ni inspeccionar el contenedor del Backend.
- E2E de red Backend → GenAI (spec 010, G09).
- Cambiar contratos HTTP, modelos de dominio ni el proveedor LLM.
- Añadir Key Vault, bases de datos, `docker-compose`, dependencias nuevas en
  `pyproject.toml` ni un entorno `staging` de GitHub.
- Instalar ni configurar un proveedor real de IA distinto del ya existente.

## Requisitos funcionales

- **RF-01:** PR y push a `main` ejecutan `ruff check .`, `mypy src` y `pytest` como gates
  bloqueantes; el escaneo de dependencias sigue siendo informativo.
- **RF-02:** en PR se construye la imagen sin publicarla y se escanea; se generan SBOM
  CycloneDX y SPDX como artefacto.
- **RF-03:** en `main` se publica la imagen con tag `sha-<SHA-completo>`, sin tags mutables,
  y se exponen el digest y las attestations de procedencia y SBOM.
- **RF-04:** el job de despliegue pertenece al entorno `production` con aprobación
  requerida, usa OIDC y despliega únicamente el digest publicado.
- **RF-05:** la identidad OIDC se asigna a un rol personalizado en el ámbito exclusivo de
  `/subscriptions/<sub>/resourceGroups/rg-thehouse-u2/providers/Microsoft.App/containerApps/ca-thehouse-genai-u2`,
  sin `listSecrets` ni permisos sobre el grupo de recursos, la suscripción, el entorno
  `cae-thehouse-u2` ni Log Analytics.
- **RF-06:** la Container App usa ingreso interno, puerto 8000, `minReplicas=1`,
  `maxReplicas=1`, 0.25 vCPU / 0.5 GiB, probes liveness/readiness/startup, secretos de ACA
  para las credenciales, variables de producción y diagnostic settings a `log-thehouse-u2`.
- **RF-07:** el gating de despliegue consulta estado de revisión, réplicas y probes de ACA;
  la verificación puntual se hace con `az containerapp exec` dentro del contenedor de GenAI
  contra `localhost:8000`, sin tocar el Backend.
- **RF-08:** existe un runbook de rollback por activación de la revisión anterior y se
  prueba una vez antes de cerrar la spec.
- **RF-09:** acciones fijadas por SHA verificado en release oficial; `Server` suprimido con
  `--no-server-header`; HSTS tratado en el borde, no en la aplicación; ningún secreto en
  YAML, imagen, logs ni documentación.

## Criterios de aceptación

- [ ] CI actual en verde y bloqueante, sin cambios en sus tres gates.
- [ ] `.dockerignore` y `Dockerfile` construidos y probados en CI, sin Docker local.
- [ ] Imagen base fijada por digest verificado y registrado con fuente y fecha.
- [ ] Dependencias con hashes y test de deriva entre `pyproject.toml` y el lock.
- [ ] PR construye y escanea sin publicar; `main` publica por SHA y digest con SBOM.
- [ ] Todas las acciones fijadas por SHA de release oficial, sin valores de memoria.
- [ ] OIDC con federated credential del entorno `production` y rol de alcance único.
- [ ] Bicep aplicado por el usuario; CI solo actualiza imagen y gestiona revisiones.
- [ ] Ingreso interno, una réplica, probes, secretos y variables verificados.
- [ ] Gating por revisión/probes y verificación `exec` en GenAI documentada.
- [ ] Rollback por revisión probado y registrado.
- [ ] `ruff check .`, `mypy src`, `pytest` y `git diff --check` en verde.
- [ ] Evidencia real registrada antes de marcar IMPLEMENTED.

## Seguridad y privacidad

- El secreto de la suscripción es OIDC: no hay client secret en el workflow, en variables
  ni en la imagen. Los identificadores de inquilino, aplicación y suscripción son
  variables, no credenciales.
- **Alcance del rol (ajuste obligatorio):** `rg-thehouse-u2` aloja también el Backend. Una
  asignación en el grupo o en la suscripción concedería a la identidad de CI capacidad de
  modificar el Backend. El rol se asigna solo sobre `ca-thehouse-genai-u2`. Las revisiones
  son recursos hijos, por lo que las operaciones de revisión quedan cubiertas por ese mismo
  ámbito. Se usa un rol personalizado porque `Container Apps Contributor`
  (`358470bc-b998-42bd-ab17-a7e34c199c0f`) incluye comodines `*/action` que permiten
  `listSecrets` (lectura de secretos en texto plano), además de `delete` y permisos sobre
  el entorno. Fuentes: guía de permisos de Compute y "Manage secrets in Azure Container
  Apps" de Microsoft Learn.
- Permisos mínimos previstos: `Microsoft.App/containerApps/read`,
  `Microsoft.App/containerApps/write`, `Microsoft.App/containerApps/revisions/read`,
  `.../revisions/activate/action`, `.../revisions/deactivate/action`,
  `.../revisions/restart/action` y `.../revisions/replicas/read`. Sin `listSecrets`, sin
  `exec`, sin `Microsoft.Insights/*` y sin `Microsoft.App/managedEnvironments/*`.
- Si Azure exigiera `Microsoft.App/managedEnvironments/read` para actualizar una app
  existente, no se ampliará el alcance por iniciativa propia: se verificará en Cloud Shell
  y se escalará al usuario.
- Ninguna credencial, token, cuerpo de petición ni PII en logs. La app ya aplica el sobre
  único de errores y la allowlist de campos de logging; esta spec no la modifica.
- Ingreso interno permanente: GitHub Actions y la computadora local no pueden alcanzar
  `/health/ready`. El servicio no se expone ni siquiera temporalmente.
- HSTS se documenta como responsabilidad del borde; `Server` se elimina en el servidor
  HTTP. CSP permanece fuera de la aplicación por la decisión D9 de 005.

## Fuera de esta spec

Permanece fuera: exponer el servicio a internet, el E2E Backend → GenAI (010), mTLS, la
capa de pago de Gemini con tope de gasto, la agregación global de métricas y presupuesto,
la creación de un entorno `staging` y cualquier cambio en los contratos de la API. Las
decisiones D1–D14 están en `plan.md` y en `memoria.md`.

## Apéndice A — Runbook de publicación en GHCR (B4)

- El job `publish` solo existe en `push` a `main` y depende de `image` en verde. Publica
  `ghcr.io/thehouse-team/thehouse-genai:sha-<SHA completo>`; no se publica ningún tag
  mutable ni `latest`. El digest se expone como output del job y se escribe en el resumen.
- **Visibilidad del paquete:** el paquete de GHCR debe ser **PÚBLICO**. Azure Container Apps
  descargará la imagen sin credenciales de registro; si el paquete fuera privado harían
  falta credenciales de GitHub en ACA, lo que queda fuera de esta spec.
- Cómo verificarlo tras el primer push:
  1. Abrir `https://github.com/orgs/thehouse-team/packages/container/package/thehouse-genai`
     y comprobar que el paquete indica `Public`.
  2. Con `gh`: `gh api /orgs/thehouse-team/packages/container/thehouse-genai --jq .visibility`
     debe devolver `public`.
  3. Sin autenticar (para imitar a ACA): `docker pull
     ghcr.io/thehouse-team/thehouse-genai:sha-<SHA>` desde un runner limpio o una sesión sin
     `docker login` debe terminar correctamente.
  4. Si el paquete quedara privado: `Settings → Packages → thehouse-genai → Change
     visibility → Public`, y repetir la comprobación 3 antes de B5.
- No se debe publicar un tag que no haya pasado `image` (smoke + escaneo). El paquete se
  referencia por digest en el despliegue (B5), nunca por tag.
