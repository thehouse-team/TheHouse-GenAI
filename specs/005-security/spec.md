# 005-security — Seguridad de servicio e IA

- **Estado:** IMPLEMENTED
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  011-llm-provider
- **Habilita:** 006, 007, 009, 010
- **Fecha de alta:** 2026-11-08
- **Fecha de activación:** 2026-11-17
- **Última revisión:** 2026-11-17
- **Plan aprobado:** 2026-11-17
- **Cerrada:** 2026-11-17

## Objetivo

Completar la postura de seguridad para un servicio interno de IA: autenticación servicio-a-servicio, minimización de PII, defensa contra prompt injection, límites y protección de secretos.

## Contexto

G01 ya aplica límites de request, CORS restrictivo, errores seguros y logs estructurados.
G04 entregó la autenticación mínima (`X-Service-Key`), los datos no confiables delimitados,
la validación de salida y el fallback seguro. Esta spec **endurece** lo existente; no lo
rehace ni cambia el contrato HTTP de `explain-match`.

El único cliente de GenAI es TheHouse Backend, de modo que el rate limit por cliente es
efectivamente global para el tráfico legítimo. Gemini en capa gratuita limita unas
~15 RPM: el exceso se normaliza en el adaptador como `ProviderRateLimitError` y termina
en fallback 200 con `generated=false`, nunca en un error para Backend. El rate limit de
GenAI no sustituye al del proveedor: protege contra abuso si la clave de servicio se
filtra, antes de consumir cuota del proveedor.

## Alcance

### Incluido

- Threat model y data flow Backend → GenAI → proveedor (apéndice de esta spec).
- Rotación de la clave de servicio: actual y anterior válidas a la vez; nunca JWT de
  usuario final.
- Allowlist explícita de los campos que pueden llegar al prompt y test de regresión del
  schema.
- Redacción centralizada de metadatos de log (fingerprint de la clave); nunca bodies ni
  cabeceras sensibles.
- Corpus versionado de prompt injection, escape de datos no confiables y normalización
  de la salida contra homoglifos y caracteres de ancho cero.
- Rate limiting por cliente en memoria (fixed window) con 429 y `Retry-After`.
- Headers de seguridad HTTP y logging de seguridad de 401 y 429.
- Escaneo de secretos y dependencias: GitHub secret scanning, push protection y
  Dependabot (configurados en Settings por el usuario) más `pip-audit` en CI.
- Pruebas de seguridad 100% sin red y runbook como apéndice.

### Excluido

- Autenticación de usuarios finales y gestión de sesiones.
- mTLS (D2), HSTS y CSP en la aplicación (D9): requieren decisiones de despliegue en
  G09/G10.
- Presupuesto global de tokens: el presupuesto por llamada ya existe; uno global
  requiere estado compartido.
- Moderación de contenido (006) y observabilidad avanzada (007).
- Pentest externo, cumplimiento legal completo, infraestructura de despliegue y CD.
- Creación de `docs/` (D7).

## Requisitos

- **RF-01:** solo health es público; todo endpoint generativo exige autenticación de
  servicio. 003 ya incorpora `X-Service-Key`; esta spec añade rotación con dos claves
  válidas y rate limiting. mTLS queda fuera (D2).
- **RF-02:** se rechazan y no se reenvían access/refresh tokens de usuario
  (`extra="forbid"` más la allowlist del prompt).
- **RF-03:** allowlist explícita de los 12 campos que pueden llegar al prompt, con un
  test que falla si el schema crece sin actualizarla.
- **RF-04:** logs y errores redactan tokens, API keys, passwords y PII mediante
  allowlist de campos de log y fingerprint; nunca se registran bodies ni credenciales.
- **RF-05:** rate limit por cliente (fingerprint de la clave) en memoria: fixed window
  de 60 peticiones / 60 s, 429 con sobre estándar y `Retry-After`. El presupuesto por
  llamada ya lo cubren `GuardedProvider` y `max_output_tokens`; un presupuesto global
  y el límite multi-instancia quedan documentados para G09/G10.
- **RF-06:** GitHub secret scanning, push protection, Dependabot (dependency alerts,
  malware alerts y security updates) y CodeQL default setup se activaron en Settings el
  2026-11-17 (D8; evidencia por capturas fuera del repo). `pip-audit` se ejecuta en CI
  con `continue-on-error`. Sin dependencias nuevas en `pyproject.toml`.
- **RF-07:** los intentos de inyección en la entrada se escapan y se registran como
  metadato seguro, sin rechazar la request (D5); la salida se normaliza con NFKC, tabla
  de confusables y eliminación de caracteres de ancho cero (D6).

## Criterios de aceptación

- [ ] Threat model y data flow documentados (apéndice).
- [ ] Endpoint generativo sin credencial devuelve 401 con sobre estándar (ya cubierto en
      003; re-verificado).
- [ ] Rotación: clave actual y anterior aceptadas; solo anterior → 401 (D10);
      comparación contra todas con `|=`; `SERVICE_KEY_PREVIOUS` genérica ignorada.
- [ ] Tokens de usuario rechazados/no reenviados.
- [ ] Allowlist de campos del prompt con test que falla si se agrega uno nuevo.
- [ ] Corpus versionado de prompt injection, sin red; salida normalizada contra
      homoglifos y ancho cero.
- [ ] Rate limit 429 con sobre estándar y `Retry-After`; limitación por proceso
      documentada.
- [ ] Headers de seguridad en todas las respuestas; OpenAPI apagada fuera de
      `local`/`test` (ya implementado; re-verificado).
- [ ] Logs de 401 y 429 con `request_id` y `reason`, sin clave ni body; fingerprint en
      429 (D12).
- [ ] Escaneo documentado (secret scanning, push protection, Dependabot) y `pip-audit`
      en CI con `continue-on-error`.
- [ ] Gates en verde y evidencia registrada antes de marcar `IMPLEMENTED`.

## Seguridad y privacidad

- Secretos solo en entorno/gestor; nunca en repo, imagen ni logs.
- Autenticación de servicio con secreto rotable: actual y anterior válidas a la vez
  durante la ventana de rotación, sin mTLS en este incremento (D2). Parte de la
  autenticación mínima de 003 y la endurece; no la sustituye.
- Defensa en profundidad: validación de entrada, prompt delimitado, validación de salida
  y normalización contra homoglifos.
- Minimización estricta de PII: allowlist de los 12 campos del prompt; el contrato no
  incluye nombre del propietario, dirección exacta ni tokens.
- Fail closed: si falla la autenticación o la validación, no se llama al proveedor.
  Tampoco se autentica si solo existe la clave anterior (D10).
- La inyección en datos de entrada se escapa y se registra, nunca se rechaza (D5).

## Decisiones aprobadas

| # | Decisión |
| --- | --- |
| D1 | Mantener la rama `feature/security-hardening` (ya creada). |
| D2 | mTLS fuera de 005; documentado para G09/G10. |
| D3 | Rate limit por `sha256` truncado de la clave; sin pepper, IP ni headers falsificables. |
| D4 | Fixed window 60/60 habilitado por defecto; `Retry-After` entero. |
| D5 | Inyección en entrada: escape y log, sin rechazo. |
| D6 | Salida: NFKC + tabla de confusables (cirílico y griego comunes: а, е, о, р, с, і, у, х…) + ancho cero. |
| D7 | Runbook como apéndice de esta spec; sin `docs/`. |
| D8 | Secret scanning, push protection, Dependabot (alerts, malware alerts, security updates) y CodeQL default setup activados en Settings el 2026-11-17 (capturas fuera del repo); `pip-audit` en CI con `continue-on-error`; sin gitleaks ni deps nuevas. |
| D9 | Sin HSTS ni CSP en la app; decidir en despliegue. |
| D10 | Fail closed si solo hay clave anterior. |
| D11 | Corpus JSON versionado en `tests/fixtures/prompt_injection_corpus.json`. |
| D12 | Fingerprint del cliente en los logs de 429. |

## Rate limiting y operación

El único cliente es Backend, así que el rate limit por fingerprint es efectivamente
global para el tráfico legítimo. El límite se aplica **antes** de llamar al proveedor:
un request sin credencial válida no consume cupo, para que un atacante sin clave no
pueda agotar el bucket de Backend. El endpoint de health queda sin auth y sin límite.

El estado del limitador vive en memoria del proceso: con N réplicas el límite efectivo
es N× el configurado. No hay Redis ni base de datos; si el servicio se escala, la
decisión global se traslada al gateway en G09/G10. Gemini en capa gratuita limita
~15 RPM y su exceso ya degrada a fallback 200 con `generated=false`: el 429 de GenAI
es una capa adicional que evita consumir esa cuota si la clave se filtra.

## Deuda para G09

- Caché de explicaciones en Backend para no repetir llamadas idénticas.
- Manejo del 429 como «sin explicación» (no como error de usuario), con el fallback ya
  existente de 003.
- Rate limit global en el gateway, mTLS, HSTS/CSP y cabecera `Server` del despliegue.

## Apéndice — Runbook de incidentes

### Threat model y flujo de datos

Backend → GenAI → proveedor (Gemini). Backend es el **único** cliente y envía el contexto
ya validado a `POST /api/v1/generative/explain-match` con `X-Service-Key`. GenAI no
consulta propiedades ni calcula el score: delimita y escapa los datos no confiables,
construye el prompt, llama al proveedor detrás del puerto y valida la salida. Los
secretos de servicio y del proveedor nunca entran en el prompt ni en los logs. Las
amenazas cubiertas son credencial de servicio filtrada o compartida, abuso de coste,
inyección en texto libre y fuga de PII o secretos a logs. El rate limit es por proceso;
la visión global y el mTLS se deciden en G09/G10.

### (a) Rotación de la clave de servicio

1. Generar la nueva clave y conservar la anterior; **no retirarla todavía**.
2. Desplegar GenAI con `GENAI_SERVICE_KEY=<nueva>` y `GENAI_SERVICE_KEY_PREVIOUS=<anterior>`.
   Ambas son válidas durante la ventana. Verificar `explain-match` con cada clave.
3. Cambiar la clave que envía Backend a la nueva y confirmar que no aparecen nuevos
   `auth.rejected` con `reason=invalid_key`.
4. Cuando todo el tráfico use la nueva, retirar `GENAI_SERVICE_KEY_PREVIOUS` y verificar
   que la clave antigua vuelve a dar 401.
5. Si no hay clave actual configurada, el servicio falla cerrado (D10): restaurar
   `GENAI_SERVICE_KEY` antes de investigar.

### (b) Fuga de credencial

- **Clave de servicio:** rotar siguiendo (a) de inmediato; revisar `auth.rejected`
  (`request_id`, `reason`) y `rate_limit.rejected` (`client_id`, `reason`) buscando picos.
  Si se detectó abuso, subir temporalmente el límite o bloquear en el gateway.
- **Clave de Gemini:** revocarla en AI Studio, generar una nueva, actualizar
  `GENAI_API_KEY` y reiniciar; revisar `provider.call.failed` y el consumo de cuota del
  proyecto. Nunca pegar la clave en el ticket.
- En ambos casos: retirar cualquier registro que la contenga, rotar y revisar la
  allowlist de `JsonFormatter`.

### (c) Ajuste del rate limit

Editar `GENAI_RATE_LIMIT_REQUESTS` y `GENAI_RATE_LIMIT_WINDOW_SECONDS` (60/60 por defecto)
y reiniciar. `Retry-After = ceil(window - transcurrido)`, mínimo 1. El estado es por
proceso: con N réplicas el efectivo es N× el valor configurado. Antes de subirlo,
comprobar el número de réplicas y la cuota de Gemini: el exceso del proveedor ya degrada
a fallback 200 con `generated=false` (D18 de 003). Verificar con `rate_limit.rejected`.

### (d) Avisos de GitHub

- **Push protection:** un commit intenta subir un secreto y GitHub lo bloquea. No se
  omite la protección ni se reescribe para ocultarlo: eliminar el valor del archivo,
  rotar la credencial expuesta y volver a hacer commit.
- **Dependabot alerts / malware alerts:** revisar la dependencia afectada, actualizar a
  la versión corregida y cerrar el alert; los security updates llegan como PR.
- **CodeQL default setup:** revisar el hallazgo, comprobar si es alcanzable en este
  servicio y corregirlo o documentar la excepción; no desactivar el análisis.

### Inyección detectada

`fallback_reason=INJECTION_MARKER` con el nombre del campo; la request no se rechaza (D5).
Escalar si aparece en varios campos o de forma sostenida. Ante secretos en logs, retirar
el registro y rotar la credencial implicada.

## Fuera de esta spec

Esta spec quedó `IMPLEMENTED` en G05 sobre la rama `feature/security-hardening`, con
criterios verificados, gates en verde y evidencia registrada. Quedan fuera de alcance
mTLS (D2), autenticación de usuarios, moderación (006), observabilidad avanzada (007),
`parse-search` (004/008), HSTS y CSP en la aplicación (D9), presupuesto global de tokens,
pentest y despliegue. El runbook es este apéndice (D7); no se crea `docs/`.
