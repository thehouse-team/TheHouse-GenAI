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

## Apéndice B — Runbook de infraestructura y OIDC (B5)

Todo se ejecuta en Azure Cloud Shell, en este orden. No se despliega nada desde GitHub:
el CI solo valida `infra/genai.bicep` con `az bicep lint` / `az bicep build` (sin
credenciales, sin `az login`).

### 1. Crear la Container App con Bicep (los secretos no entran al historial)

```bash
SUB=$(az account show --query id -o tsv)
IMAGE='ghcr.io/thehouse-team/thehouse-genai@sha256:8b5d250ce96cd338cab3ec2c0547e8c34704c1ec13c711ed019038d79e2b9edf'
read -rs -p 'GENAI_API_KEY: ' K_API; echo
read -rs -p 'GENAI_SERVICE_KEY: ' K_SVC; echo
read -rs -p 'GENAI_METRICS_KEY: ' K_MET; echo
read -rs -p 'GENAI_SERVICE_KEY_PREVIOUS (vacío si no rotas): ' K_PREV; echo

az deployment group create \
  --resource-group rg-thehouse-u2 \
  --template-file infra/genai.bicep \
  --parameters imageDigest="$IMAGE" \
               genaiApiKey="$K_API" genaiServiceKey="$K_SVC" \
               genaiMetricsKey="$K_MET" genaiServiceKeyPrevious="$K_PREV"
unset K_API K_SVC K_MET K_PREV
```

Las variables se introducen con `read -rs` (no se muestran ni quedan en el historial de la
shell). Para mayor garantía frente a la lista de procesos, se puede generar un archivo de
parámetros temporal con `umask 077` y borrarlo al terminar. Nunca se versiona un
archivo de parámetros con secretos. El template no crea ni modifica `cae-thehouse-u2`
(usamos `existing`) y no configura credenciales de registro: la imagen es pública en GHCR.

**Proyecto de AI Studio para producción:** `GENAI_API_KEY` debe venir de un proyecto de
AI Studio **separado** (por ejemplo `thehouse-genai-prod`). Las cuotas y límites de Gemini
son por proyecto, así que no debe compartirse con el desarrollo local ni con los smoke
manuales de las specs 004/011. Ese proyecto es el que usará el despliegue con
`GENAI_BUDGET_ENABLED=true` y `GENAI_DAILY_CALL_LIMIT=400`.

### 2. Identidad OIDC y rol con alcance de un solo recurso

```bash
APP=$(az ad app create --display-name thehouse-genai-gh-actions)
APP_ID=$(echo "$APP" | jq -r .appId)          # Application (client) ID
APP_OBJ=$(echo "$APP" | jq -r .id)            # Object ID
TENANT=$(az account show --query tenantId -o tsv)

SP_OBJ=$(az ad sp create --id "$APP_ID" --query id -o tsv)

cat > /tmp/genai-fic.json <<'JSON'
{
  "name": "thehouse-genai-production",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:thehouse-team/TheHouse-GenAI:environment:production",
  "description": "GitHub Actions production environment",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON
az ad app federated-credential create --id "$APP_OBJ" --parameters /tmp/genai-fic.json
```

El `subject` debe coincidir exactamente con el `environment: production` del workflow;
Microsoft Entra no avisa si hay un error de escritura, solo falla el intercambio de tokens.

```bash
SCOPE="/subscriptions/$SUB/resourceGroups/rg-thehouse-u2/providers/Microsoft.App/containerApps/ca-thehouse-genai-u2"
cat > /tmp/genai-role.json <<JSON
{
  "Name": "TheHouse GenAI Deploy (scoped)",
  "IsCustom": true,
  "Description": "Update image and revisions of ca-thehouse-genai-u2 only",
  "Actions": [
    "Microsoft.App/containerApps/read",
    "Microsoft.App/containerApps/write",
    "Microsoft.App/containerApps/revisions/read",
    "Microsoft.App/containerApps/revisions/activate/action",
    "Microsoft.App/containerApps/revisions/deactivate/action",
    "Microsoft.App/containerApps/revisions/restart/action",
    "Microsoft.App/containerApps/revisions/replicas/read"
  ],
  "NotActions": [],
  "AssignableScopes": ["$SCOPE"]
}
JSON
az role definition create --role-definition /tmp/genai-role.json
az role assignment create --assignee "$SP_OBJ" \
  --role "TheHouse GenAI Deploy (scoped)" --scope "$SCOPE"
rm -f /tmp/genai-fic.json /tmp/genai-role.json
```

Los permisos se verificaron en B0 contra la referencia oficial de permisos de Compute y la
guía de secretos de ACA. Se excluyen `listSecrets`, `exec`, `Microsoft.Insights/*` y
`managedEnvironments/*`. El alcance es **solo la Container App**, nunca
`rg-thehouse-u2` (que también contiene el Backend). Si la CLI pidiera
`Microsoft.App/managedEnvironments/read`, no ampliar el alcance: verificar en Cloud Shell
y escalar la decisión.

### 3. Variables del entorno `production` en GitHub

En `Settings → Environments → production` (con aprobación requerida) crear las variables
`AZURE_CLIENT_ID=$APP_ID`, `AZURE_TENANT_ID=$TENANT`, `AZURE_SUBSCRIPTION_ID=$SUB`. No son
secretos, pero viven en el entorno protegido. No se crea ningún client secret.

### 4. Verificación

```bash
az containerapp show --name ca-thehouse-genai-u2 --resource-group rg-thehouse-u2 \
  --query properties.configuration.ingress.fqdn -o tsv
az containerapp revision list --name ca-thehouse-genai-u2 --resource-group rg-thehouse-u2 \
  --query '[].{name:name,state:properties.state,health:properties.healthState}' -o table
```

El FQDN interno debe tener el segmento `.internal.`. El tráfico HTTP interno entre apps
del mismo entorno se resuelve por DNS de ACA (se puede llamar a
`http://ca-thehouse-genai-u2`). Según Microsoft Learn, el proxy de ACA redirige HTTP a
HTTPS en el puerto 80 salvo que `allowInsecure: true`; por eso el Bicep lo activa: el
Backend llama por HTTP y el tráfico **nunca sale del entorno**. Es una decisión acotada al
ingreso interno; el servicio no tiene endpoint externo.

### 5. Rollback (coherente con `activeRevisionsMode: Single`)

El Bicep fija `activeRevisionsMode: 'Single'`: no se pueden activar revisiones antiguas
ni repartir tráfico entre ellas. El rollback consiste en **redesplegar el último digest
conocido como bueno**, lo que crea una revisión nueva que pasa a ser la activa. El job
`publish` ya publica cada imagen con un tag inmutable `sha-<SHA>` y escribe el digest en el
resumen del run; `evidence.md` de la spec 009 es el historial de digests desplegados
(con su fecha y resultado de verificación). B6 seguirá exactamente este enfoque: nunca
reactivar una revisión anterior.

Para saber qué digest está corriendo ahora:

```bash
az containerapp show --name ca-thehouse-genai-u2 --resource-group rg-thehouse-u2 \
  --query properties.template.containers[0].image -o tsv
```

Con ese valor como `imageDigest`, reaplicar el Bicep (paso 1) crea la revisión de
rollback. Después verificar con `az containerapp revision list ...` y las probes.

### 6. Advertencia antes de cualquier reaplicación del Bicep

**Siempre consultar primero el digest en ejecución** con el comando anterior y pasarlo a
`--parameters imageDigest=...`. `infra/genai.bicep` toma la imagen como parámetro sin
valor por defecto: si se reaplica con un digest distinto (por ejemplo el del último
`publish`, aunque sea más reciente) se revertirá la imagen **sin aviso**. Antes de
reaplicar: consultar digest actual, decidir si se quiere mantener o promover uno nuevo,
y solo entonces ejecutar el deployment.

### 7. Limpieza del intento fallido de App Service

Si el grupo vacío `thehouse-genai_group` sigue existiendo:

```bash
az resource list --resource-group thehouse-genai_group -o table   # confirmar que está vacío
az group delete --name thehouse-genai_group --yes --no-wait
```
