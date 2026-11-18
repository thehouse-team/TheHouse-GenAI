# Memoria del proyecto — TheHouse GenAI

Última actualización: 2026-11-18

## Identidad

Repositorio independiente para IA generativa de TheHouse. Recibe contexto calculado por
TheHouse Backend y produce explicaciones o filtros. No sustituye al Backend, no calcula
Smart Match, no consulta propiedades y no contiene Mobile.

## Estado de specs

| Spec | Estado | Alcance |
| --- | --- | --- |
| 001-foundation | IMPLEMENTED | Servicio mínimo, health, config, seguridad base, tests, CI |
| 002-provider-abstraction | IMPLEMENTED | Puerto `GenerativeAiProvider`, DTOs, errores, fake y factory (offline) |
| 003-smart-match-explanation | IMPLEMENTED | Explicación de match sin alterar hechos, con auth mínima de servicio |
| 004-natural-language-search | PLANNED | Parseo de búsqueda a filtros, nunca propiedades |
| 005-security | IMPLEMENTED | Autenticación de servicio endurecida, PII, prompt injection |
| 006-moderation | IMPLEMENTED | Política y moderación de la salida generativa (alcance A) |
| 007-observability | PLANNED | Métricas, trazas, SLOs y alertas |
| 008-testing | PLANNED | Estrategia completa y contract tests (transversal, cierra en G09) |
| 009-ci-cd | PLANNED | Pipeline completo y despliegue futuro |
| 010-integration-thehouse | PLANNED | Contratos y operación con Backend |
| 011-llm-provider | IMPLEMENTED | Evaluación de proveedores y adaptador real detrás del puerto |

## Mapeo de fases

| Fase | Spec | Contenido |
| --- | --- | --- |
| G01 | 001-foundation | Servicio base, health, configuración, CI (IMPLEMENTED) |
| G02 | 002-provider-abstraction | Puerto LLM, DTOs, errores, fake y factory, 100% offline (IMPLEMENTED) |
| G03 | 011-llm-provider | Evaluación de proveedores y adaptador real (IMPLEMENTED) |
| G04 | 003-smart-match-explanation | Endpoint explain-match con auth mínima de servicio |
| G05 | 005-security | Endurecimiento de seguridad, PII, prompt injection |
| G06 | 006-moderation | Moderación de la salida generativa (IMPLEMENTED) |
| G07 | 007-observability | Observabilidad, métricas y SLOs |
| G08 | 004-natural-language-search | Endpoint parse-search con auth endurecida |
| G09 | 010-integration-thehouse | Integración con Backend; cierra 008-testing |
| G10 | 009-ci-cd | Pipeline completo y despliegue |

`008-testing` es transversal: sus entregables (contract tests, corpus de seguridad,
cobertura) se acumulan en cada fase y la spec se cierra en G09, junto con
`010-integration-thehouse`, que es la que exige contract tests y E2E en staging.

## Spec activa

Ninguna. `006-moderation` (G06) se cerró como `IMPLEMENTED` el 2026-11-18 sobre la rama
`feature/moderation` con el **alcance A** aprobado: política `moderation_v1`, puerto de
moderación con fake y moderador local determinista, moderación de la **salida** de
`explain-match`, plantilla sin título ni presupuesto y `safetySettings` en Gemini.
Criterios verificados, gates en verde, 688 tests sin red y evidencia registrada en
`specs/006-moderation/evidence.md`. Sin endpoint de contenido de usuarios, sin LLM de
moderación y sin dependencias nuevas. La prueba manual real del 2026-11-18 con
`gemini-3.5-flash-lite`, `safetySettings` y moderación local devolvió una explicación
fiel con `generated=true`; la mojibake observada en PowerShell 5 se debió al cliente
de prueba (`Invoke-RestMethod`), no al servicio, y queda documentada para G09.

`005-security` (G05) se cerró como `IMPLEMENTED` el 2026-11-17 sobre la rama
`feature/security-hardening` con criterios verificados, gates en verde y 536 tests sin
red. Endureció la autenticación de servicio de 003 sin rehacerla: rotación de clave,
rate limiting en memoria, minimización de PII, corpus de prompt injection, headers de
seguridad, logging de 401/429 y escaneo en CI. `003-smart-match-explanation` (G04) se
cerró como `IMPLEMENTED` el 2026-11-17 con
criterios verificados, gates en verde, 409 tests sin red y evidencia registrada en
`specs/003-smart-match-explanation/evidence.md`, incluidas las pruebas reales con
`gemini-3.5-flash-lite`. `011-llm-provider` (G03) pasó a `IMPLEMENTED` el 2026-11-16 con
sus criterios verificados, los gates en verde y la evidencia registrada en
`specs/011-llm-provider/evidence.md`, incluido el smoke test manual ejecutado con una
credencial real el 2026-11-16. `001-foundation`, `002-provider-abstraction`, 003 y 005
permanecen `IMPLEMENTED` y el resto de specs, `PLANNED`. Solo una spec puede estar
`ACTIVE` a la vez; ahora mismo ninguna lo está.

## Enmiendas de la constitución

- **Enmienda 1.1 (2026-11-12).** Artículo 8: los estados de una spec son `PLANNED` →
  `ACTIVE` → `IMPLEMENTED` y solo una spec puede estar `ACTIVE` a la vez. Sustituye la
  regla anterior de una sola spec `IMPLEMENTED`. Artículo 5: el adaptador concreto de
  proveedor se define en la spec 011. Registrada en `constitution.md`, sección
  "Enmiendas".

## Decisiones tomadas en 001

- Python 3.12 + FastAPI + Pydantic v2 + pydantic-settings; sin Docker.
- Paquete `thehouse_genai` bajo `src/`, instalable con `pip install -e ".[dev]"`.
- Configuración tipada y validada al arrancar. Valores inválidos fallan con error claro.
- `GENAI_API_KEY` se modela como `SecretStr`; no se usa en G01.
- CORS vacío por defecto; se rechazan comodines y orígenes no HTTP(S).
- Límite de request (`MAX_REQUEST_BYTES`) aplicado antes de la lógica de aplicación.
- ID de correlación saneado, eco en `X-Request-ID` y logging JSON sin secretos.
- Sobre de error único: `{"error": {"code", "message", "request_id"}}`.
- Health: `GET /health/live` y `GET /health/ready`, ambos 200 con payload estable.
- Documentación OpenAPI solo en `local` y `test`.
- CI bloqueante con ruff, mypy y pytest; sin CD ni despliegue.

## Decisiones de gobernanza (2026-11-12)

- G02 es 100% offline: protocolo `GenerativeAiProvider`, DTOs inmutables, taxonomía de
  errores, `FakeProvider`, factory, timeout obligatorio y límite de entrada. No existe
  adaptador de red en esa fase.
- El adaptador real y la evaluación de proveedores (Gemini, OpenAI, Azure OpenAI) pasan a
  la spec `011-llm-provider` (G03), detrás del mismo puerto.
- El proveedor se elige por precio, capa gratuita, latencia, salida JSON estructurada,
  calidad en español e integración en Python; la decisión queda documentada en la spec.
- Los tests de `011-llm-provider` corren sin red; el smoke test contra una credencial
  real es un script manual opt-in que CI nunca ejecuta.
- `003-smart-match-explanation` incluye autenticación mínima servicio-a-servicio
  (`X-Service-Key`, `SecretStr` en `Settings`, comparación en tiempo constante, 401 con
  el sobre estándar) para cumplir el artículo 7; `005-security` la endurece.
- El mapeo de fases queda en la tabla anterior y `008-testing` se cierra en G09.
- El trabajo se hace en ramas `feature/<spec>` o `chore/<tema>`, nunca en `main`; todo
  merge entra por pull request con squash y con el checklist SDD.

## Contrato de health

```json
{"status": "ok", "service": "thehouse-genai", "version": "0.1.0"}
```

## Configuración futura reservada

`GENAI_PROVIDER`, `GENAI_API_KEY`, `GENAI_MODEL`, `GENAI_TIMEOUT_SECONDS` (15) y
`GENAI_MAX_INPUT_CHARS` (4000). En G01 y G02 no se usan para llamadas externas: 002 solo
los valida y la factory solo admite `fake`; 011 los consume en el adaptador real.

## Decisiones tomadas en 002

- D-1: puerto, DTOs, taxonomía de errores y guard viven en `providers/base.py`;
  `domain/` y `application/` no se modificaron en G02 ni importan implementaciones de
  proveedor.
- D-2: el timeout no forma parte de la firma del puerto; un guard central lo aplica con
  `asyncio.wait_for` y cancela la operación interna al excederlo.
- D-3: el timeout se prueba por doble vía: inyección de `TimeoutError` sin espera y
  `hang` con timeout de 0,05 s.
- D-4: los tests async usan `asyncio.run` dentro de tests síncronos; no se añadió
  `pytest-asyncio` ni se tocó `pyproject.toml`.
- D-5: `UnsupportedProviderError` deriva de `ValueError` y queda fuera de la taxonomía
  `ProviderError`: es un fallo de configuración, no de una llamada.
- D-6: el límite de entrada mide `len(prompt) + len(system_prompt)` y solo compara
  longitudes.
- D-7: los DTOs fijan prompt, system prompt, formato de respuesta, temperatura y tokens
  máximos; la respuesta añade uso, motivo de fin y modelo interno.
- D-8: una excepción inesperada del proveedor se normaliza a `ProviderUnavailableError`
  y un `ValidationError` a `ProviderInvalidResponseError`, ambos con la causa
  encadenada.
- D-9: `FakeProvider` registra las requests recibidas en memoria, solo para aserciones
  de test; nunca se registran ni se serializan.
- D-10: `pyproject.toml` no se modificó en G02.
- D-11: el guard se implementó en `providers/base.py`, dentro de los archivos previstos.
- D-12: G02 no añadió logging ni amplía la allowlist del logging JSON.
- D-13: `README.md` se actualizó al activar la spec.
- D-14: `Settings.genai_provider` es `Literal["fake"]` opcional y la factory revalida
  el nombre: doble barrera contra un proveedor real.
- D-15: las decisiones quedan documentadas en la spec activa; no hay plan fuera del
  repositorio.

## Decisiones tomadas en 011

Proveedor elegido: **Gemini API (Google AI Studio)**, familia Flash, por REST con
`httpx` y sin SDK nuevo. El id del modelo se fija con `GENAI_MODEL` y no se
hardcodea en el código. La matriz comparativa y las fuentes están en
`specs/011-llm-provider/evaluation.md`; el documento de decisión completo, en
`specs/011-llm-provider/decision.md`.

- D-1: el `400` del vendor se mapea a `ProviderInvalidResponseError`; no se crean
  clases nuevas en `providers/base.py` ni se modifica la taxonomía de 002.
- D-2: el `404` (modelo inexistente) se mapea también a `ProviderInvalidResponseError`,
  por ser un fallo no reintentable de configuración.
- D-3: el timeout de `httpx` es igual a `GENAI_TIMEOUT_SECONDS`, además del timeout
  total que aplica `GuardedProvider`; ambos caminos terminan en
  `ProviderTimeoutError`.
- D-4: la allowlist del logging JSON amplía con `provider`, `provider_model`,
  `error_code`, `duration_ms`, `prompt_chars` y `completion_chars`. Nunca se
  registra contenido: ni prompts, ni respuestas, ni cabeceras.
- D-5: el adaptador vive en `src/thehouse_genai/providers/gemini.py`.
- D-6: el cliente `httpx` se crea por llamada; no hay cliente compartido ni ciclo de
  vida que cerrar.
- D-7: `temperature` se envía siempre, aunque algunas familias de Gemini lo ignoren;
  el smoke test registra las cabeceras de deprecación que devuelva el vendor.
- D-8: el smoke test de 011 (bloque B8) se ejecuta en la capa gratuita con prompts
  sintéticos. El proyecto de pago con tope de gasto se crea antes de la demo con
  datos reales, en la fase G09.
- D-9: no hay modelo por defecto en el repositorio; `GENAI_MODEL` vacío significa
  "no configurado" y es un error si el proveedor es `gemini`.
- D-10: `GENAI_TIMEOUT_SECONDS` mantiene el valor por defecto de 15 s.
- D-11: el adaptador no valida que el JSON devuelto parsea; el puerto devuelve texto y
  el esquema de negocio lo validan 003 y 004.
- D-12: la spec no se cierra como `IMPLEMENTED` sin un smoke test real ejecutado y
  registrado en `evidence.md`.
- D-13: la factory incorpora `ProviderConfigurationError`, subclase de `ValueError`
  ajena a la taxonomía, para credencial o modelo ausentes con proveedor `gemini`.
- D-14: `GENAI_PROVIDER` sin definir sigue lanzando `UnsupportedProviderError`; no
  hay proveedor por defecto.
- D-15: `GENAI_API_KEY` y `GENAI_MODEL` vacíos o con solo espacios se normalizan a
  `None` (se cierra la deuda de 002); con `GENAI_PROVIDER=gemini` ambos son
  obligatorios al arrancar y el mensaje de error nunca incluye el valor de la
  credencial.
- D-16: el adaptador registra `provider.call.completed` y `provider.call.failed` con
  `provider`, `provider_model`, `error_code`, `duration_ms`, `prompt_chars` y
  `completion_chars`; nunca el prompt, la respuesta, las cabeceras ni la credencial.
  El estado HTTP se inspecciona antes de parsear el cuerpo, de modo que la página de
  error del vendor nunca llega a una excepción ni a un log.
- D-17: la presencia de una cabecera de deprecación del vendor se señala con un
  registro propio (`provider.call.deprecation`), sin volcar ni el nombre ni el valor
  de la cabecera; el detalle lo verá el script de smoke test (B7).
- D-18: la factory admite `fake` y `gemini`; el proveedor real se construye como
  `GuardedProvider(GeminiProvider(...))` con el timeout y el límite de entrada de
  `Settings`. `ProviderConfigurationError`, subclase de `ValueError` ajena a la
  taxonomía, cubre la credencial o el modelo ausentes o inválidos: es un fallo de
  configuración, no de una llamada.
- D-19: `scripts/smoke_provider.py` es una utilidad manual opt-in: si la variable
  `CI` está activa sale con código 2 sin hacer nada; si no, exige `--i-have-a-real-key`
  o `GENAI_SMOKE=1` y una confirmación escrita (`SI`, o `--yes` para omitirla). No
  imprime la credencial, solo su longitud, y solo usa el puerto del proveedor.
- D-20: los scripts pueden usar el paquete (incluida la factory), pero no importar
  clientes HTTP ni SDKs de proveedor: el barrido de fronteras los cubre. El paquete
  publica `py.typed` para que `mypy --strict` pueda comprobar los scripts.

## Decisiones tomadas en 003

Plan aprobado el 2026-11-17. Contrato alineado con el borrador que Backend ya revisa.

- D-1: contrato HTTP camelCase con aliases sobre modelos Python snake_case y
  `extra="forbid"`. Nombres: `matchScore`, `distanceKm`, `budgetMax`,
  `essentialServices`, `maxDistanceKm`, `promptVersion`.
- D-2: la respuesta es exactamente `{explanation, generated, promptVersion}`. Sin
  `facts_used` (queda como artefacto interno del validador), sin score como campo y sin
  metadatos del proveedor. Se actualiza `spec.md` en consecuencia.
- D-3: el modelo puede mencionar el porcentaje, siempre idéntico a `matchScore` y
  validado; el score se trata como hecho autoritativo, nunca recalculado ni presentado
  como propio (Art. 2).
- D-4: fallo del proveedor, timeout o salida rechazada → 200 con `generated=false` y
  plantilla de fallback. Se elimina el 502 del plan; el fallback no es un error para
  Backend.
- D-5: proveedor no configurado o fallido degrada con log `ERROR` y responde fallback;
  la validación estricta de `Settings` sigue en arranque, pero el readiness del
  proveedor queda para la spec 007.
- D-6: `locale` opcional con default `es-MX`; cualquier otro valor da 422.
- D-7: `university` es `str` (espera confirmación de Backend sobre la forma del dato).
- D-8: credencial de servicio en `Settings` como `SecretStr | None`, env
  `GENAI_SERVICE_KEY`; vacía o solo espacios se normaliza a `None` y la auth falla
  cerrado.
- D-9: 422 si `property.currency != preferences.currency`; no se inventa conversión.
- D-10: medir en B5 el tamaño real de system prompt + contexto antes de decidir si se
  sube `GENAI_MAX_INPUT_CHARS` (4000 por defecto; el guard cuenta ambos textos).
- D-11: en B1 se alinea `AGENTS.md` para no prohibir `explain-match` (ya no es futuro) y
  se reescribe «Fuera de esta spec».
- D-12: vocabulario inicial de servicios en `domain`: `internet`, `agua`, `luz`, `gas`,
  `estacionamiento`, `lavadora`, `amueblado`, `baño privado`, `mascotas`.
- D-13: normalizar todos los números a decimal antes de compararlos con los del input.
- D-14: `MALFORMED_TEXT` detecta palabras pegadas con prefijo funcional + sufijo del
  dominio y allowlist de colisiones reales (`porque`, `conque`, `delimite`), para evitar
  falsos positivos con `conde`, `conforme`, `delante` o `debajo`.
- D-15: prompt `explain_match_v2` según el primer feedback real de Gemini; v1 queda
  histórica.
- D-16: logger `httpx` en WARNING para conservar solo los logs estructurados propios.
- D-17: normalizar solo espacios antes de validar (corrección tipográfica sin alterar
  hechos) en lugar de rechazar; prompt `explain_match_v3`: sin saludos ni exclamaciones,
  empieza con la propiedad y usa `%` en vez de «por ciento». v2 queda histórica.
- D-18: GenAI debe cortar antes que el Backend. Recomendación de producción:
  `GENAI_TIMEOUT_SECONDS=6` en GenAI y timeout de 8 s en el cliente del Backend, por el
  pico real de 9639 ms en la capa gratuita. El default de `Settings` sigue en 15 s; se
  aplica en G09/G10.

Ajustes obligatorios incorporados al diseño y a la spec:

1. Regla 4 del system prompt: «no lo completes ni lo deduzcas» (se corrigen caracteres
   CJK del borrador).
2. Rama de trabajo: la actual `feature/smart-match-explanation`.
3. Plantilla de fallback neutra y factual, sin «No se pudo generar»; la coincidencia se
   atribuye a las preferencias del estudiante, no a la universidad.
4. `price` y `budgetMax` como `Decimal` (ge 0, máximo 2 decimales), no `int`.
5. Servicios: rechazar solo caracteres de control y longitud > 40; sin regex
   restrictiva; delimitadores como `<untrusted_data>` se escapan en `to_context()`.

## Decisiones tomadas en 005

Plan aprobado el 2026-11-17. Decisiones D1–D12 registradas al activar la spec:

| # | Decisión |
| --- | --- |
| D1 | Mantener la rama `feature/security-hardening` (ya creada) en lugar de renombrarla. |
| D2 | mTLS queda fuera de 005: requiere TLS/certificados en despliegue. Se documenta para G09/G10. |
| D3 | Identidad del rate limit: `sha256` truncado de la clave presentada, sin pepper; nunca la clave en claro ni IP/headers falsificables. |
| D4 | Fixed window de 60 peticiones / 60 s, habilitado por defecto; `Retry-After` entero. |
| D5 | Inyección en datos de entrada: se escapa y se registra como metadato seguro, nunca se rechaza; no altera el contrato con Backend. |
| D6 | Normalización de salida: NFKC + tabla de confusables (cirílico/griego comunes: а, е, о, р, с, і, у, х…) + eliminación de caracteres de ancho cero. NFKC por sí solo no convierte cirílico a latino. |
| D7 | Runbook como apéndice de `specs/005-security/spec.md`; no se crea `docs/`. |
| D8 | Secret scanning, push protection, Dependabot (alerts, malware alerts, security updates) y CodeQL default setup activados en Settings el 2026-11-17 (capturas fuera del repo). CI añade `pip-audit` con `continue-on-error`; no se usa gitleaks ni se añaden dependencias a `pyproject.toml`. |
| D9 | Omitir HSTS y CSP en la aplicación; se deciden en despliegue (G09/G10). |
| D10 | Si no hay clave actual, fallar cerrado aunque exista `GENAI_SERVICE_KEY_PREVIOUS`. |
| D11 | Corpus de inyección versionado en `tests/fixtures/prompt_injection_corpus.json`. |
| D12 | Los logs de 429 incluyen el fingerprint del cliente (hash truncado), nunca la clave. |

Las doce decisiones se aplicaron íntegramente; el detalle está en
`specs/005-security/spec.md` y los resultados en `specs/005-security/evidence.md`.

## Decisiones tomadas en 006

Plan aprobado el 2026-11-18 para el alcance A. Quedan fuera de G06 el endpoint de
moderación de contenido de usuarios y el uso del LLM como moderador.

| # | Decisión |
| --- | --- |
| A1 | Alcance A únicamente: reglas deterministas locales sobre la salida de `explain-match` más `safetySettings` en `generateContent`. Sin endpoint de contenido de usuarios. |
| A2 | Fail-closed en salida: ante decisión adversa o error del moderador se responde 200 con `generated=false` y la plantilla de fallback; nunca 500 ni un campo nuevo en la respuesta. |
| A3 | `safetySettings`: cuatro categorías centrales de Gemini con umbral `BLOCK_MEDIUM_AND_ABOVE`, como constante en `providers/gemini.py` y sin variable de entorno nueva. Es refuerzo del proveedor, no el mecanismo de moderación. |
| A4 | Cero llamadas extra a Gemini: las reglas locales no consumen cuota y los `safetySettings` viajan en la misma petición. Sin modo híbrido en G06. |
| A5 | RF-02 se reformula: «toda salida generativa pasa por el puerto de moderación; la entrada de `explain-match` sigue cubierta por 003/005 (escape y registro, sin rechazo, D5 de 005)». |
| A6 | La plantilla de fallback de `explain-match` **no incluye el título de la propiedad ni el presupuesto**: el título lo escribe el arrendador y puede traer PII, ofensas o inyección (observado en G04); el presupuesto es una preferencia del estudiante. La plantilla usa solo datos estructurados: score, precio con moneda, distancia, universidad y servicios. Sin cambiar el contrato `{explanation, generated, promptVersion}`. |
| A7 | Para la opción B, cuando se active: fail-closed = `review` (Backend no publica hasta revisión humana) y LLM solo con flag opt-in. Queda documentado como decisión anticipada, sin implementar en G06. |

Las decisiones A1–A7 se aplicaron íntegramente en los bloques B1–B6 y la spec se cerró
como `IMPLEMENTED` el 2026-11-18, con la evidencia y el mapeo criterio→test registrados
en `specs/006-moderation/evidence.md`. A6 se implementó en B4, incluida la actualización
de los tests de 003 y 006.

El único cliente es Backend, así que el rate limit por cliente es efectivamente global
para el tráfico legítimo. Gemini en capa gratuita limita ~15 RPM y el exceso termina en
fallback 200 con `generated=false`; el rate limit de GenAI protege contra abuso si la
clave se filtra, antes de consumir cuota del proveedor. Deuda para G09: caché de
explicaciones en Backend y manejo del 429 como «sin explicación».

## Evidencia resumida

### 001-foundation

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict).
- `pytest`: 21 tests aprobados.
- Commit de bootstrap: `chore: bootstrap generative ai service`.

### 002-provider-abstraction

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 18 archivos.
- `pytest`: 148 tests aprobados (102 en `test_providers.py`, 20 en `test_config.py`, 9 en
  `test_import_boundaries.py`, 8 en `test_provider_factory.py`, 5 en `test_errors.py` y 4
  en `test_health.py`), con el guard de red activo.
- Rama `feature/provider-abstraction`: 6 commits, uno por bloque de implementación.
- Evidencia completa en `specs/002-provider-abstraction/evidence.md`.

### 011-llm-provider

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 19 archivos.
- `mypy --strict scripts/smoke_provider.py`: sin errores.
- `pytest`: 279 tests aprobados (102 en `test_providers.py`, 57 en
  `test_provider_adapter.py`, 53 en `test_import_boundaries.py`, 33 en `test_config.py`,
  17 en `test_provider_factory.py`, 8 en `test_smoke_script.py`, 5 en `test_errors.py` y
  4 en `test_health.py`), con el guard de red activo.
- Smoke test manual ejecutado el 2026-11-16 con `gemini-3.5-flash-lite` en capa
  gratuita: seis llamadas sin errores, latencia entre 817.0 ms y 1461.3 ms, español
  natural sin datos inventados y JSON válido.
- Rama `feature/llm-provider`: 8 commits, uno por bloque.
- Evidencia completa en `specs/011-llm-provider/evidence.md`.

### 003-smart-match-explanation

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 23 archivos.
- `pytest`: 409 tests aprobados, sin red (guard `block_network`), 1 warning heredado de
  `TestClient` (deuda de 008).
- Pruebas reales con `gemini-3.5-flash-lite` en capa gratuita, prompts v1 → v2 → v3:
  inyección ignorada 4 de 4, 401 sin clave con mensaje genérico, auth antes de validar
  el body. Última ronda (v3): 1406 ms caso normal y 9639 ms caso de inyección.
- Rama `feature/smart-match-explanation`: 8 commits (B1–B7b más el cierre documental).
- Evidencia completa en `specs/003-smart-match-explanation/evidence.md`.

### 005-security

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 25 archivos.
- `pytest`: 536 tests aprobados, sin red (guard `block_network`), 1 warning heredado de
  `TestClient` (deuda de 008).
- Prueba manual real del 2026-11-17 con Gemini y `GENAI_RATE_LIMIT_REQUESTS=2`: dos 200
  y un tercer 429 con `Retry-After` sin llamar al proveedor; los cuatro headers de
  seguridad presentes también en los errores.
- Rama `feature/security-hardening`: 8 commits (B0–B7 más el cierre documental).
- Evidencia completa en `specs/005-security/evidence.md`.

## Deuda y pendientes

- `GENAI_API_KEY=` y `GENAI_MODEL=` vacíos quedaban como `SecretStr('')` y `''` en lugar
  de `None`; normalizados en 011, bloque B2.
- El logging estructurado de las llamadas al proveedor (modelo, duración, `error_code`)
  se inicia en 011 con la allowlist ampliada (D-4) y se completa en 007.
- Usar contexto es-MX en los prompts reales de 004: moneda en MXN y formato de fecha y
  hora UTTT. En 003 ya se aplica (MXN, UTTT, español de México). El smoke test de 011 no
  fija esta convención porque su objetivo es medir latencia y calidad con datos
  sintéticos.
- La confirmación interactiva de `scripts/smoke_provider.py` acepta «si» en minúsculas
  porque normaliza a mayúsculas; no es un fallo, pero conviene decidir si se exige
  mayúscula estricta.
- El precio por millón de tokens del modelo de desarrollo
  (`gemini-3.5-flash-lite`) queda por anotar desde la fuente de precios, y el modelo de
  producción se decide cuando se cree el proyecto de pago (G09).
- Contratos y guardrails de parseo (004). Los de explicación (003) están cerrados.
- `005-security` quedó `IMPLEMENTED` en G05; la auth mínima de 003 sigue vigente y mTLS
  queda para G09/G10 (D2).
- Deuda (a): el rate limit es por proceso; revisar el límite efectivo con varias
  instancias y trasladarlo al gateway en G10.
- Deuda (b): HSTS y la cabecera `Server` se deciden en despliegue (G10); CSP queda fuera
  de la aplicación (D9).
- Deuda (c): caché de explicaciones en Backend y manejo del 429 como «sin explicación»
  (no como error de usuario) en G09.
- Deuda (d): un body que no es JSON válido se rechaza al parsearse, antes de la
  autenticación (422 en TestClient, 400 en la prueba manual real). El mensaje es genérico
  y no expone datos; no se cambió el orden de procesamiento. Evaluar en G09/G10 si Backend
  debe validar el body antes de enviarlo.
- Timeouts de producción (D18): `GENAI_TIMEOUT_SECONDS=6` en GenAI y 8 s en el cliente
  del Backend, pendiente de aplicar en G09/G10. El default de `Settings` sigue en 15 s
  y el pico real de 9639 ms queda registrado en la evidencia de 003.
- Variabilidad de latencia en la capa gratuita (9639 ms en el peor caso de 003):
  reevaluar con la capa de pago antes de la demo con datos reales (G09).
- Vocabulario de servicios D12 (`internet`, `agua`, `luz`, `gas`, `estacionamiento`,
  `lavadora`, `amueblado`, `baño privado`, `mascotas`) pendiente de confirmar con
  Backend; es detector de alucinaciones, no una restricción de entrada.
- Deuda (e): `StarletteDeprecationWarning` de `TestClient` con `httpx`: se mantiene y se
  revisa en 008.
- Deuda 006-(a): la opción B (moderación de contenido de usuarios: títulos y descripciones
  de propiedades, reseñas y reportes) quedó fuera del alcance A. Si el requisito
  académico la exige, se abre como **spec nueva** dependiente de 006, con el contrato
  propuesto en el plan y la decisión A7 (fail-closed `review`, LLM solo con flag opt-in).
- Deuda 006-(b): el léxico de moderación se amplía con el uso, a mano y en PR por el
  equipo de TheHouse; el archivo de datos y `test_shipped_lexicon_is_well_formed` son la
  única fuente de términos reales.
- Deuda 006-(c): monitorizar `fallback_reason` `MODERATION_BLOCKED`, `MODERATION_REVIEW`
  y `MODERATION_UNAVAILABLE`, además de `PROVIDER_ERROR`, para detectar un exceso de
  bloqueos por `safetySettings` o falsos positivos del léxico. Se decide en 007 con las
  métricas y alertas.
- Deuda 006-(d): se mantiene el `StarletteDeprecationWarning` de `TestClient` con
  `httpx`; se revisa en 008. Es la misma deuda (e) ya registrada.
- Observabilidad avanzada, contract tests e integración (007–010).
- No hay despliegue. Hay una credencial de desarrollo en el entorno local, fuera del
  repositorio: la capa gratuita de Gemini se usa solo con prompts sintéticos.

## Próximo paso

G07 = `007-observability`: métricas, trazas, SLOs y alertas, donde se decide el
readiness del proveedor y se instrumentan los motivos `MODERATION_*` y `PROVIDER_ERROR`
(deuda 006-(c)). Le siguen G08
(`004-natural-language-search`) y G09/G10, donde se aplican los timeouts de producción
de D18 y se decide el despliegue (incluidos mTLS, HSTS/CSP, la cabecera `Server` y el
rate limit global, deudas (a) y (b) de 005). `004-natural-language-search` permanece
`PLANNED`.
