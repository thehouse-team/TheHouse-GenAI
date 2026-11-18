# 007-observability — Observabilidad

- **Estado:** IMPLEMENTED
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  005-security, 006-moderation, 011-llm-provider
- **Habilita:** 009-ci-cd, 010-integration-thehouse
- **Fecha de alta:** 2026-11-08
- **Activada:** 2026-11-18, con plan aprobado y decisiones 1–9 registradas en `memoria.md`

## Objetivo

Dar visibilidad operativa al servicio sin exponer prompts, respuestas, claves ni PII:
métricas en memoria del proceso, logs correlacionados, un presupuesto diario configurable
de uso del proveedor, endpoints internos de diagnóstico y SLOs con alertas documentadas
para el despliegue de G10.

## Contexto

G01 ya emite logs JSON con `request_id` y health probes; 002/011 añadieron el puerto del
proveedor y el uso de tokens reportado por Gemini; 003 fijó el contrato de `explain-match`
y el fallback seguro; 005 añadió auth, rate limit y logs de 401/429; 006 añadió las
decisiones de moderación y la deuda 006-(c) de monitorizar `MODERATION_*` y
`PROVIDER_ERROR`. Gemini en capa gratuita: ~15 RPM, 250K TPM, 500 RPD; latencia típica
de 1,3 a 1,8 s con picos reales de 9,6 s. G10 desplegará en Azure, donde podrá usarse
Application Insights; esa integración queda **documentada, no implementada**, en esta spec.

## Alcance

### Incluido

- Schema de logs estable y allowlist de campos (apéndice A).
- Correlación de una request completa mediante `request_id` inyectado en los logs por un
  filtro que lee el `ContextVar`; sin `trace_id`, sin librería de trazas y sin enviar el
  `request_id` al proveedor.
- Métricas en memoria: peticiones por endpoint y status, latencia (media, p50 y p95
  aproximados por histograma), llamadas al proveedor, éxito/fallback por
  `fallback_reason`, decisiones de moderación, 401, 429 y tokens de entrada/salida
  reportados por Gemini.
- Coste estimado por modelo con tarifas configurables por millón de tokens; 0 por defecto.
- Presupuesto diario configurable de llamadas y, opcionalmente, de tokens, con zona
  `UTC-6` fija; al agotarse, `explain-match` responde 200 con fallback y
  `fallback_reason=BUDGET_EXHAUSTED`, sin llamar a Gemini.
- Dos endpoints internos protegidos con `X-Service-Key` independiente:
  `GET /internal/metrics` (JSON) y `GET /internal/health/detail` (siempre 200 con
  `status`).
- SLOs, alertas para G10, retención y muestreo documentados (apéndice B).
- Pruebas de no-fuga: ningún contenido, credencial ni PII en logs ni en métricas.

### Excluido

- Contratar APM, desplegar dashboards ni configurar Application Insights en G10.
- Formato Prometheus ni la dependencia `prometheus-client`: el contrato de G07 es JSON.
- Nueva dependencia de cualquier tipo, incluido `tzdata`: se usa un offset fijo `UTC-6`.
- Cambiar el payload de `/health/live` o `/health/ready` (contrato de G01).
- Añadir campos al contrato `{explanation, generated, promptVersion}` de `explain-match`.
- Registrar prompts, respuestas, títulos, universidades, claves ni PII.
- Moderación de contenido de usuarios (opción B de 006), trazas distribuidas con spans,
  agregación entre réplicas ni store compartido de presupuesto.

## Requisitos

- **RF-01:** todo log usa JSON con timestamp, nivel, logger, mensaje y `request_id` cuando
  existe contexto de request; solo se emiten los campos de la allowlist.
- **RF-02:** las métricas cubren latencia, errores por código, proveedor, moderación,
  seguridad y saturación, con etiquetas de enum cerrado. La latencia se separa por
  `status_class` (`2xx`, `4xx`, `5xx`, `other`) para que los rechazos rápidos no distorsionen
  el SLO.
- **RF-03:** nunca se registran ni se exponen prompts, respuestas, tokens de credencial,
  headers, bodies ni PII. Los contadores de tokens de Gemini son metadatos agregados.
- **RF-04:** el `request_id` se correlaciona en todos los logs de una request Through el
  filtro de logging; nunca se envía en el cuerpo ni en las cabeceras de Gemini.
- **RF-05:** SLOs y alertas documentados con umbrales iniciales (apéndice B), a
  recalibrar con datos de staging en G10.
- **RF-06:** retención = vida del proceso; muestreo = 100% de los contadores (baratos).
  La persistencia y agregación se documentan para G10 (apéndice C).
- **RF-07:** presupuesto diario desactivado por defecto; `GENAI_DAILY_CALL_LIMIT=400` y
  límites de tokens opcionales (`None` = sin límite). Al agotarse, fallback 200 con
  `BUDGET_EXHAUSTED`; la activación se decide en el despliegue de G10.
- **RF-08:** los endpoints internos exigen `GENAI_METRICS_KEY` (`SecretStr | None`, fail
  closed); el detalle de readiness nunca cambia el contrato de los probes de G01.
- **RF-09:** la latencia se resume con buckets fijos de 50, 100, 250, 500, 1000, 2000,
  5000, 10000 ms y `+Inf`; p50 y p95 se interpolan dentro del bucket y se documentan como
  aproximados.

## Criterios de aceptación

- [ ] Schema de logs documentado (apéndice A) y probado.
- [ ] Métricas expuestas internamente con nombres estables y etiquetas acotadas.
- [ ] Una request completa se correlaciona por `request_id` en API, proveedor y caso de uso.
- [ ] SLOs y alertas aprobados y documentados para G10.
- [ ] Pruebas garantizan ausencia de contenido sensible en logs y en el snapshot JSON.
- [ ] Coste y tokens medidos sin almacenar texto.
- [ ] Presupuesto diario: sin llamada a Gemini al agotarse; `BUDGET_EXHAUSTED` solo en
      log/métrica; contrato de `explain-match` intacto.
- [ ] `/internal/metrics` y `/internal/health/detail` protegidos, con sobre de error único.
- [ ] `/health/live`, `/health/ready` y su payload sin cambios.
- [ ] Sin dependencias nuevas; suite 100% sin red.

## Seguridad y privacidad

- Ninguna etiqueta libre: todos los valores salen de enums cerrados definidos en el puerto
  de métricas de `application/`.
- La ruta se normaliza a un conjunto acotado; el resto se agrupa como `other`. Nunca se
  expone la URL cruda, query strings ni IDs de request.
- `X-Service-Key` de generación y `X-Service-Key` de métricas son credenciales distintas;
  ambas se comparan en tiempo constante y nunca se registran.
- No se expone el id interno del modelo del proveedor en métricas; solo el nombre del
  proveedor (`fake`/`gemini`) como metadato acotado.
- Sin stack traces, mensajes de vendor ni detalles internos en ninguna respuesta.

## Apéndice A — Esquema de logs

Campos emitidos por `JsonFormatter` (el resto del `LogRecord` se descarta):

| Campo | Origen |
| --- | --- |
| `timestamp`, `level`, `logger`, `message` | siempre |
| `request_id` | middleware de contexto; inyectado por el filtro en los logs de proveedor y caso de uso |
| `method`, `path`, `status_code`, `duration_ms` | `http.request.completed` |
| `provider`, `provider_model`, `error_code`, `duration_ms`, `prompt_chars`, `completion_chars` | `provider.call.*` |
| `generated`, `prompt_version`, `fallback_reason` | `explain_match.completed` / `explain_match.fallback` |
| `moderation_decision`, `moderation_category`, `policy_version` | moderación |
| `reason`, `client_id`, `retry_after_seconds` | `auth.rejected`, `rate_limit.rejected` |
| `exception` | solo en excepciones no controladas |

`client_id` es un hash truncado de la clave, nunca la clave. Las longitudes de prompt y
completion son metadatos, no contenido. El campo `environment` no está en la allowlist y
por tanto no se emite.

## Apéndice B — SLOs y alertas documentadas (G10)

Valores iniciales a recalibrar con datos de staging (decisión 7):

| SLO | Objetivo inicial | Medición |
| --- | --- | --- |
| Disponibilidad HTTP | ≥ 99,9% de respuestas no-5xx en 30 días | el fallback 200 no cuenta como caída |
| Latencia `explain-match` | p95 ≤ 2,5 s, p99 ≤ 6,5 s en 28 días | Solo respuestas **2xx** (`status_class=2xx`); p99 acotado por D18 |
| Fallback inesperado | ≤ 2% (`PROVIDER_ERROR`, `INVALID_JSON`, `MODERATION_UNAVAILABLE`) | sobre peticiones válidas |
| Moderación | `MODERATION_BLOCKED` ≤ 1% | cierra deuda 006-(c) |
| Saturación propia | 429 ≤ 1% de peticiones válidas | — |
| Presupuesto | aviso al 80%; alerta ante el primer `BUDGET_EXHAUSTED` | — |

El SLO de latencia **solo** considera la serie `status_class=2xx` de
`http_request_duration_ms` en `explain-match`. Las series `4xx` (por ejemplo un 401
casi instantáneo) y `5xx` se reportan aparte y no entran en el cálculo de p50/p95: la
prueba manual del 2026-11-18 mostró que mezclarlas deformaba el p50 hasta 50 ms. La
etiqueta es de enum cerrado, por lo que la cardinalidad sigue acotada.

Alertas a documentar para Application Insights / Azure Monitor en G10, **sin implementar
aquí**: p95 > 2,5 s por 10 min; 5xx > 0,1% por 5 min; fallback inesperado > 2% por 15 min;
`MODERATION_BLOCKED` > 5% por 15 min; 429 > 1% por 5 min; pico de 401 > 10/min;
presupuesto < 20%; `BUDGET_EXHAUSTED > 0`; aviso de RPM/TPM acercándose a 15/250K de la
capa gratuita. Requiere exportar los contadores a `customMetrics` en G10.

## Apéndice C — Limitaciones

- Las métricas y el presupuesto son **por proceso**: se pierden al reiniciar y, con N
  réplicas, el presupuesto efectivo es N× el configurado (misma deuda (a) de 005).
  G10: agregación en Azure Monitor y cupo global en gateway/API Management o store
  compartido, con spec aprobada.
- Un balanceador puede responder `/internal/metrics` desde cualquier instancia: el
  snapshot no es global.
- p50/p95 son aproximados por interpolación de buckets; no hay spans ni `trace_id`.
- El offset `UTC-6` es fijo porque CDMX eliminó el horario de verano en 2022. La cuota
  diaria de Gemini se reinicia a medianoche **hora del Pacífico**, así que los días no
  coinciden exactamente: el exceso termina en fallback, nunca en error.
- Los precios por millón de tokens los configura el operador; no se consulta ninguna
  fuente externa.

## Fuera de esta spec

Spec cerrada como `IMPLEMENTED` el 2026-11-18 con criterios verificados, gates en verde y
evidencia registrada. Las tareas y resultados viven en `plan.md`, `task.md`,
`checklist.md` y `evidence.md`. La prueba manual real de los endpoints internos queda
pendiente de que el usuario la proporcione.
