// Azure Container App for TheHouse GenAI (spec 009, B5).
// The Container Apps environment already exists and is referenced as `existing`:
// this template never creates or modifies cae-thehouse-u2 / log-thehouse-u2.
// The environment already sends app console logs to log-thehouse-u2.

@description('Region of the existing environment.')
param location string = 'eastus2'

@description('Full image reference by immutable digest: ghcr.io/thehouse-team/thehouse-genai@sha256:...')
param imageDigest string

@secure()
@description('Gemini API credential. Supplied interactively; never versioned.')
param genaiApiKey string

@secure()
@description('Service-to-service key shared with TheHouse Backend.')
param genaiServiceKey string

@secure()
@description('Separate key for the internal diagnostics endpoints.')
param genaiMetricsKey string

@secure()
@description('Outgoing service key during rotation. Pass an empty string when not rotating.')
param genaiServiceKeyPrevious string

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: 'cae-thehouse-u2'
}

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: 'ca-thehouse-genai-u2'
  location: location
  tags: {
    application: 'thehouse-genai'
    environment: 'production'
  }
  properties: {
    environmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        // Internal ingress: only other apps in cae-thehouse-u2 can reach this app.
        external: false
        targetPort: 8000
        transport: 'auto'
        // ACA redirects HTTP to HTTPS on port 80 unless allowInsecure is true.
        // The Backend calls http://ca-thehouse-genai-u2; traffic never leaves the
        // environment (per Microsoft Learn: communicate between container apps).
        allowInsecure: true
      }
      secrets: concat(
        [
          { name: 'genai-api-key', value: genaiApiKey }
          { name: 'genai-service-key', value: genaiServiceKey }
          { name: 'genai-metrics-key', value: genaiMetricsKey }
        ],
        empty(genaiServiceKeyPrevious) ? [] : [
          { name: 'genai-service-key-previous', value: genaiServiceKeyPrevious }
        ]
      )
    }
    template: {
      containers: [
        {
          name: 'thehouse-genai'
          image: imageDigest
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/health/live', port: 8000, scheme: 'HTTP' }
              initialDelaySeconds: 5
              periodSeconds: 5
              timeoutSeconds: 2
              failureThreshold: 10
            }
            {
              type: 'Liveness'
              httpGet: { path: '/health/live', port: 8000, scheme: 'HTTP' }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 2
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health/ready', port: 8000, scheme: 'HTTP' }
              initialDelaySeconds: 5
              periodSeconds: 5
              timeoutSeconds: 2
              failureThreshold: 3
            }
          ]
          env: concat(
            [
              { name: 'APP_ENV', value: 'production' }
              { name: 'GENAI_PROVIDER', value: 'gemini' }
              { name: 'GENAI_MODEL', value: 'gemini-3.5-flash-lite' }
              { name: 'GENAI_TIMEOUT_SECONDS', value: '6' }
              { name: 'GENAI_BUDGET_ENABLED', value: 'true' }
              { name: 'GENAI_DAILY_CALL_LIMIT', value: '400' }
              { name: 'GENAI_COST_INPUT_PER_MILLION', value: '0' }
              { name: 'GENAI_COST_OUTPUT_PER_MILLION', value: '0' }
              { name: 'GENAI_RATE_LIMIT_ENABLED', value: 'true' }
              { name: 'GENAI_RATE_LIMIT_REQUESTS', value: '60' }
              { name: 'GENAI_RATE_LIMIT_WINDOW_SECONDS', value: '60' }
              { name: 'GENAI_RATE_LIMIT_MAX_CLIENTS', value: '1000' }
              { name: 'GENAI_MAX_INPUT_CHARS', value: '4000' }
              { name: 'LOG_LEVEL', value: 'INFO' }
              { name: 'GENAI_API_KEY', secretRef: 'genai-api-key' }
              { name: 'GENAI_SERVICE_KEY', secretRef: 'genai-service-key' }
              { name: 'GENAI_METRICS_KEY', secretRef: 'genai-metrics-key' }
            ],
            empty(genaiServiceKeyPrevious) ? [] : [
              { name: 'GENAI_SERVICE_KEY_PREVIOUS', secretRef: 'genai-service-key-previous' }
            ]
          )
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
