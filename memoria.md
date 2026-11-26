# Memoria del proyecto — TheHouse GenAI

Última actualización: 2026-11-26

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
| 004-natural-language-search | IMPLEMENTED | Parseo de búsqueda a filtros, nunca propiedades |
| 005-security | IMPLEMENTED | Autenticación de servicio endurecida, PII, prompt injection |
| 006-moderation | IMPLEMENTED | Política y moderación de la salida generativa (alcance A) |
| 007-observability | IMPLEMENTED | Métricas en memoria, presupuesto diario, endpoints internos, SLOs y alertas documentadas |
| 008-testing | PLANNED | Estrategia completa y contract tests (transversal, cierra en G09) |
| 009-ci-cd | IMPLEMENTED | Imagen endurecida, CI/CD, OIDC y despliegue en ACA (G10) |
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
| G07 | 007-observability | Observabilidad, métricas y SLOs (IMPLEMENTED) |
| G08 | 004-natural-language-search | Endpoint parse-search con auth endurecida (IMPLEMENTED) |
| G09 | 010-integration-thehouse | Integración con Backend; cierra 008-testing |
| G10 | 009-ci-cd | Pipeline completo y despliegue |

`008-testing` es transversal: sus entregables (contract tests, corpus de seguridad,
cobertura) se acumulan en cada fase y la spec se cierra en G09, junto con
`010-integration-thehouse`, que es la que exige contract tests y E2E en staging.

## Spec activa

**Ninguna spec está ACTIVE** desde el 2026-11-22.

`009-ci-cd` (G10) se cerró como **IMPLEMENTED** el 2026-11-22. El CD con aprobación se
verificó en CI #39 (PR #19): login OIDC, despliegue por digest
`sha256:a5e6051b…` y verificación de la revisión `0000005` tras tres intentos
`NOT_READY` (`Activating`/`None`) y un cuarto `RunningAtMaxScale`/`Healthy` → `VERIFIED`.
El rollback se probó en producción ese mismo día (`0000006` con `47670b63` y roll-forward
`0000007` con `a5e6051b`, ambos verificados; transición de tráfico resuelta en 2 minutos).
El Bicep se reaplicó con el digest en ejecución (revisión `0000008`, `allowInsecure=false`,
escalado 0→1 y regla `http-concurrency`). Cierre B7–B8: `-o none` en `update` y gate de
tráfico exclusivo (100 % en la revisión nueva, sin otra activa con tráfico; desvíos =
ESPERAR). Decisiones D1–D27, evidencia y deudas registradas abajo. `008-testing` y
`010-integration-thehouse` permanecen `PLANNED`.

## Corrección G10 sobre 002 y 003 (2026-11-26)

Autorización del usuario: corrección de G10 sobre las specs **IMPLEMENTED** 002 y 003,
en la rama `fix/genai-resilience` creada desde `origin/main` (`89e7f8c`). No hay
ninguna spec `ACTIVE`; 002 y 003 siguen `IMPLEMENTED` y `010-integration-thehouse`
sigue `PLANNED`. No se hizo push y no se abrieron llaves ni secretos.

### Hechos recibidos y verificados en el repositorio

- **#21** (`16090f9`, autor IsaiAxel, 2026-11-24, «fix: prevent false unknown service
  rejection»): cambió únicamente `application/explain_match.py` para envolver la
  búsqueda de servicios conocidos en `\b`. No tocó ninguna spec ni añadió pruebas.
  Quedó verificado que, con `services=["agua caliente"]`, el texto «agua caliente»
  seguía disparando `UNKNOWN_SERVICE`.
- **#22** (`89e7f8c`, autor IsaiAxel, 2026-11-25, «fix: bound GenAI provider latency for
  NV-24»): bajó el default de `GENAI_TIMEOUT_SECONDS` de 15 a 7, añadió dos capas
  `apt-get` en el `Dockerfile` (zlib1g y libzstd1), añadió `request_id` explícito en los
  logs de `providers/gemini.py` vía `api.request_context` y actualizó el test de
  configuración afectado. También versionó `git_diff.txt` y `test_output.txt`. No
  actualizó ninguna spec; la única prueba fue el ajuste de un valor por defecto ya
  existente, sin cobertura del cambio de logging.
- **Evidencia de producción** (Log Analytics, 24–26 nov, según el reporte del operador):
  4 de 19 llamadas a Gemini fallaron con `PROVIDER_UNAVAILABLE` en ~0.6 s y degradaron
  a `explain_match.fallback` con `PROVIDER_ERROR`. La credencial y el modelo estaban
  correctos (curl directo 5/5 = 200); son fallas pasajeras y no se reintentaban aunque
  la taxonomía marca `retryable=True`. El mismo reporte cita las revisiones de ACA
  `0000009` y `0000010`; el repositorio no contiene sus digests ni datos de tráfico,
  así que no se inventan.
- **`CVE-2026-124851`** verificado el 2026-11-26 en
  `https://security-tracker.debian.org/tracker/CVE-2026-124851`: existe, afecta a
  libzstd 1.5.1–1.5.7 y la entrada de `trixie (security)` fija
  `1.5.7+dfsg-1+deb13u1`, que es exactamente la versión ya fijada en el `Dockerfile`.
  El ID del comentario es correcto; no se cambió el `Dockerfile`.

### Cambios y decisiones de la corrección

- Bloque 1 (`fb67882`): `provider.call.failed` añade `http_status` (solo el número,
  cuando hubo respuesta) o `transport_error` (`type(exc).__name__`, cuando fue
  `httpx.HTTPError` sin respuesta); nunca mensaje, cuerpo ni cabeceras. Se eliminó el
  import de `api.request_context` y los `request_id` explícitos del adaptador: la
  correlación la sigue inyectando `RequestIdFilter` de `infrastructure/logging.py`.
  La allowlist del logging incorpora `http_status` y `transport_error`.
- Bloque 2 (`0f405a7`, ajustado por revisión en `fix: drop 429 retry and reserve budget
  after deadline check`): `RetryingProvider` en `providers/` aplica **un** reintento
  solo ante `ProviderUnavailableError`; espera fija de 300 ms inyectable (`sleep`) y
  reloj inyectable. No reintenta ante Auth, InvalidResponse, `ProviderRateLimitError`
  ni Timeout: en la capa gratuita un 429 significa que se agotó la cuota por minuto, así
  que reintentar a los 300 ms solo consumiría más presupuesto. Solo reintenta si el
  primer intento duró <2.5 s y el total cabe en `GENAI_TIMEOUT_SECONDS + 1 s`; la
  factory lo envuelve con `GuardedProvider`, cuyo timeout (7 s) es el límite real de la
  secuencia. Cada intento consume el presupuesto diario: el caso de uso reserva el
  primero y el decorador reserva el reintento, pero solo después de verificar el plazo
  tras el sleep; un plazo vencido o un cupo agotado no consumen slot ni reintentan.
  Evento `provider.call.retry` con `attempt`,
  `error_code` y `request_id` (inyectado por el filtro del logger del decorador). No
  se añadió ninguna etiqueta de métrica: los contadores existentes registran el
  desenlace final de cada caso de uso y contar también cada intento duplicaría
  `provider_calls_total`. La espera es configurable por parámetro del decorador, sin
  variable de entorno nueva; los tests inyectan el sleep y no duermen.
- Bloque 3 (`c7bc809`): `_validate_explanation` enmascara con espacios, de más largo a
  más corto y con `\b` + `re.escape`, cada servicio recibido (propiedad + preferencias)
  en el texto en minúsculas antes de buscar los `KNOWN_SERVICES` con `\b`. Así se
  aceptan etiquetas compuestas recibidas sin confundir su prefijo con un servicio
  inventado.
- Bloque 4: se eliminan `git_diff.txt` y `test_output.txt` y se documentan los hechos
  anteriores. Los specs 002 y 003 mantienen su estado `IMPLEMENTED`; la corrección se
  registra en sus `evidence.md`/`checklist.md`, sin activar ninguna spec. La exclusión
  original de reintentos de la spec 002 queda así derogada solo por esta corrección
  autorizada, no por una spec nueva.

### Gates de la corrección

| Bloque | `ruff check .` | `mypy src` | `mypy --strict .github/ci/revision_status.py` | `pytest` |
| --- | --- | --- | --- | --- |
| 1 | `All checks passed!` | 36 archivos, sin errores | 1 archivo, sin errores | 1134 passed, 1 warning |
| 2 | `All checks passed!` | 37 archivos, sin errores | 1 archivo, sin errores | 1149 passed, 1 warning |
| 3 | `All checks passed!` | 37 archivos, sin errores | 1 archivo, sin errores | 1154 passed, 1 warning |
| 4 | `All checks passed!` | 37 archivos, sin errores | 1 archivo, sin errores | 1154 passed, 1 warning |
| Revisión (`drop 429 retry`) | `All checks passed!` | 37 archivos, sin errores | 1 archivo, sin errores | 1156 passed, 1 warning |

El único warning es el `StarletteDeprecationWarning` heredado de `TestClient` (deuda
`008-testing`). `git diff --check` queda limpio.

`004-natural-language-search` (G08) se cerró como **IMPLEMENTED** el 2026-11-18 sobre la
rama `feature/natural-language-search`, con plan aprobado y las decisiones D1–D13 más los
4 ajustes obligatorios registrados más abajo aplicados. Añade
`POST /api/v1/generative/parse-search` con autenticación endurecida, reutilizando 003,
005, 006, 007 y 011 sin rehacerlos. Criterios verificados, gates en verde, 1021 tests sin
red, 8 commits y evidencia en `specs/004-natural-language-search/evidence.md`. La prueba
real con `gemini-3.5-flash-lite` cerró en 29/30 exactos tras reintentos; el diagnóstico de
ps-03 reveló el bug del parser estricto, corregido sin relajar la validación. `maxBudget`
y `maxDistanceKm` se serializan como números JSON porque el contrato con Backend manda.

Hecho registrado: los bloques B0–B3 de la spec 009 entraron a `main` en el PR #9 de forma
anticipada, por un merge de un compañero sobre un borrador; el trabajo de G10 continuó en
`feature/deployment-cd` y el cierre B7–B8 en `feature/close-ci-cd`. `009-ci-cd` se activó
el 2026-11-18 con plan aprobado y la enmienda 1.2 ratificada: publicación en GHCR y
despliegue por digest en `ca-thehouse-genai-u2` (entorno `cae-thehouse-u2`, mismo que el
Backend), ingreso interno, OIDC, entorno `production` protegido y rollback por revisiones.
Ya no queda trabajo pendiente de esta spec.

`007-observability` (G07) se cerró como **IMPLEMENTED** el 2026-11-18 sobre la
rama `feature/observability` con las decisiones 1–9 aplicadas: métricas en memoria con
etiquetas cerradas e histograma, presupuesto diario desactivado por defecto con coste
`Decimal`, endpoints internos con clave separada, correlación por `request_id` y
SLOs/alertas documentadas para G10. Criterios verificados, gates en verde, 775 tests sin
red, 7 commits y evidencia en `specs/007-observability/evidence.md`. Sin dependencias
nuevas (incluido `tzdata`) y sin cambios en los contratos de health ni de `explain-match`.
La prueba manual real de los endpoints internos queda pendiente de que el usuario la
proporcione.

`006-moderation` (G06) se cerró como `IMPLEMENTED` el 2026-11-18 sobre la rama
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
- **Enmienda 1.2 (2026-11-18).** Artículo 9: autoriza `Dockerfile` + `.dockerignore` solo
  para la imagen de despliegue (sin `docker-compose` ni dependencias nuevas en
  `pyproject.toml`). Artículo 10: autoriza CD a `production` por digest con aprobación.
  Motivo: cuota 0 de App Service y consistencia con el Backend en ACA. Registrada en
  `constitution.md`, sección "Enmiendas".

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

## Decisiones tomadas en 007

Plan aprobado el 2026-11-18. Las nueve decisiones propuestas quedan aceptadas tal cual:

| # | Decisión |
| --- | --- |
| 1 | Alcance revisado aprobado: métricas, presupuesto, endpoints internos, correlación por `request_id` y SLOs documentados; dependencias ampliadas a 001, 002, 003, 005, 006 y 011; sin `infrastructure/tracing.py`. |
| 2 | Clave separada `GENAI_METRICS_KEY` (`SecretStr \| None`, fail closed) para los endpoints internos; distinta de `GENAI_SERVICE_KEY`. |
| 3 | Solo JSON en G07: sin formato Prometheus y sin `prometheus-client` ni ninguna dependencia nueva. |
| 4 | Latencia con histograma de buckets fijos (50, 100, 250, 500, 1000, 2000, 5000, 10000 ms y `+Inf`); p50/p95 aproximados por interpolación. |
| 5 | Presupuesto desactivado por defecto, `GENAI_DAILY_CALL_LIMIT=400`, límites de tokens opcionales (`None` = sin límite); su activación queda en el checklist de despliegue de G10. |
| 6 | Sin `tzdata`: offset fijo UTC-6 porque CDMX eliminó el horario de verano en 2022. La cuota diaria de Gemini se reinicia a medianoche hora del Pacífico, así que los días no coinciden exactamente; el exceso termina en fallback, no en error. |
| 7 | SLOs iniciales a recalibrar con datos de staging en G10. |
| 8 | `/internal/health/detail` siempre devuelve 200 con un campo `status`; no sustituye a los probes de G01. |
| 9 | Filtro que inyecta `request_id` en los logs; nunca se envía a Gemini y `provider_model` nunca aparece en métricas. |

Estas decisiones se aplicaron íntegramente en los bloques B0–B7, se verificaron con 775
tests sin red y se documentan en el apéndice de `specs/007-observability/spec.md` y en su
`evidence.md` (incluidos los fallos intermedios y las desviaciones).

## Decisiones tomadas en 004

Plan aprobado el 2026-11-18. Contrato acordado con Backend (borrador ajustado): request
`{query, locale}`; response `{filters{maxBudget, currency, university,
essentialServices, petsAllowed, maxDistanceKm}, confidence, generated, promptVersion}`.

| # | Decisión |
| --- | --- |
| D1 | Añadir `promptVersion` (`parse_search_v1`) a la respuesta. |
| D2 | Opción C: GenAI emite solo lo respaldado por el texto; sin catálogos en el request ni en `Settings`. Backend mapea y valida. |
| D3 | `query` de 1–500 caracteres; blank/oversized → 422; vago o solo-PII → 200 vacío + `low`. |
| D4 | Solo `MXN`: `null` sin dinero, `MXN` con dinero, otra moneda explícita → descartar `maxBudget`, `currency=null` y bajar confianza. |
| D5 | `petsAllowed` solo `true`; menciones negativas → `null`. |
| D6 | `generated=false` si se podan todos los filtros. |
| D7 | Confianza determinista: `grounded` cuenta `maxBudget`, `university`, `petsAllowed`, `maxDistanceKm` y cada servicio; `high` si ≥2 sin podas ni rango, `medium` si 1 o podas o rango, `low` en fallback/sin evidencia. |
| D8 | Moderación de entrada fail-closed sin llamada al proveedor; extensión documentada del alcance A de 006. |
| D9 | Fallback sin proveedor: filtros vacíos + `low`, sin extractor determinista. |
| D10 | Métricas y logs: ruta cerrada `parse-search`, nuevos contadores y razones, filtro de `request_id` para `application.parse_search`. |
| D11 | Extraer el guard de texto a `domain/text_guard.py` con re-exports; los tests de 003 siguen verdes sin cambios. |
| D12 | Script manual nuevo `scripts/smoke_parse_search.py`, opt-in y nunca en CI. |
| D13 | Rama `feature/natural-language-search`. |

Ajustes obligatorios incorporados al diseño:

1. `maxDistanceKm` (`Decimal | null`, ≥0, ≤100) con evidencia de `km`, `kms` o
   `kilómetro(s)`. Minutos y cuadras no se convierten. Corpus: "a menos de 2 km de la
   UTTT", "a 10 minutos de la uni" → `null`, "3 km" vs "3k".
2. `university`: el valor devuelto debe aparecer en la query normalizada (sin acentos,
   minúsculas, palabra completa) o ser la forma canónica de un alias presente. Tabla de
   alias en código, por ahora UTTT y su nombre completo. Sin evidencia, se poda.
3. "entre 2000 y 3000" → `maxBudget=3000` (tope del rango) con confianza máxima `medium`.
4. No escribir caracteres CJK ni de ancho completo en ningún archivo.

## Decisiones tomadas en 009

Plan aprobado por el usuario el 2026-11-18. Las decisiones D1–D27 (incluido el ajuste de
seguridad D14 y los cierres D26–D27) se aplicaron en los bloques B0–B8 de
`specs/009-ci-cd/plan.md`.

| # | Decisión |
| --- | --- |
| D1 | Conservar la rama `feature/deployment` (ya creada y limpia) en lugar de renombrarla a `feature/ci-cd`. |
| D2 | Ratificar la enmienda 1.2 con el texto exacto acordado, sin cambios. |
| D3 | Fijar las acciones de GitHub por SHA **durante B3**, obtenido solo de la release oficial; sin acceso web, pedir el valor al usuario y nunca escribirlo de memoria. Igual criterio para el digest de `python:3.12-slim` en B2. |
| D4 | Un único `.github/workflows/ci.yml` con los jobs `quality`, `image`, `publish` y `deploy`; el digest viaja por `needs` sin artifacts entre workflows. |
| D5 | Un único entorno protegido de GitHub: `production`. Sin entorno `staging` separado. |
| D6 | La infraestructura se define en Bicep y el usuario la aplica manualmente desde Azure Cloud Shell; el CI **solo** actualiza la imagen y gestiona revisiones. |
| D7 | Nombre de la Container App: `ca-thehouse-genai-u2`, en `cae-thehouse-u2`, `rg-thehouse-u2`, East US 2. |
| D8 | Originalmente `minReplicas=1`; **sustituido el 2026-11-19** por la política de costo $0: `minReplicas=0`, `maxReplicas=1`, regla HTTP de 10 concurrentes, `cooldownPeriod=300` y `pollingInterval=30`. Se mantiene 0.25 vCPU / 0.5 GiB. El arranque en frío se cubre con el fallback y el timeout de 6 s frente a los 8 s del Backend. |
| D9 | Secretos directos de Container Apps para las tres claves (`GENAI_SERVICE_KEY`, `GENAI_METRICS_KEY`, `GENAI_API_KEY`) y la clave anterior durante rotación. Sin Key Vault en esta spec. |
| D10 | El CI **no** obtiene lectura de Log Analytics: el workspace contiene también los logs del Backend. El gating usa únicamente estado de revisión, réplicas y probes de ACA. |
| D11 | Verificación puntual con `az containerapp exec` **dentro del contenedor de GenAI**, llamando a `localhost:8000` con Python; no se toca el contenedor del Backend. La E2E de red Backend → GenAI queda en la spec 010 (G09). |
| D12 | HSTS fuera de la aplicación: se documenta como responsabilidad del borde (ACA/gateway). CSP sigue fuera por D9 de 005. El header `Server` se suprime en el `CMD` de uvicorn con `--no-server-header`. |
| D13 | Proveedor de capa gratuita, modelo `gemini-3.5-flash-lite`, coste 0. **Se mantiene la capa gratuita** por la política de costo $0; derogada la recomendación de crear un proyecto de pago con tope de gasto. El límite real es de Gemini (500 RPD); el cupo local de 400 deja de ser exacto porque el estado se reinicia al escalar a 0. |
| D14 | **Ajuste de seguridad obligatorio:** la asignación de rol de la identidad OIDC tiene alcance **solo sobre el recurso** `ca-thehouse-genai-u2`, nunca sobre `rg-thehouse-u2` ni la suscripción, porque el grupo contiene también el Backend. Se usa un rol personalizado sin `listSecrets` en lugar de `Container Apps Contributor`, cuyos comodines `Microsoft.App/containerApps/*/action` conceden lectura de secretos en texto plano. Fuentes oficiales: `https://learn.microsoft.com/en-us/azure/role-based-access-control/permissions/compute` y `https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets`. |

La verificación del rol se reforzó contra la documentación oficial: los permisos mínimos
disponibles son `Microsoft.App/containerApps/read`, `Microsoft.App/containerApps/write`,
`Microsoft.App/containerApps/revisions/read`, `.../revisions/activate/action`,
`.../revisions/deactivate/action`, `.../revisions/restart/action` y
`.../revisions/replicas/read`. Las revisiones son recursos hijos de la Container App, por lo
que un rol asignado sobre esa app cubre también su lectura y gestión. `exec` no se concede
al CI: la decisión D11 la ejecuta el usuario manualmente. Si Azure exigiera además
`Microsoft.App/managedEnvironments/read` para `az containerapp update`, no se ampliará el
alcance por iniciativa propia: se verifica en Cloud Shell durante B4 y se escala al usuario.

Hecho registrado el 2026-11-19: el operador aplicó la infraestructura manualmente con
`infra/genai.bicep` (what-if 1 create / 6 ignore) y creó `ca-thehouse-genai-u2` con ingreso
interno, revisión `okuxih9` Active/Healthy y el digest
`sha256:6411108f02043659bde838c1ae48362e3e9f5ed8ee33b59d08adc16939a9aa71` (CI #31). El rol
efectivo es `TheHouse GenAI Deployer` con **5** acciones (sin activate/deactivate, sin
listSecrets, sin delete), asignado solo sobre la Container App. El entorno `production` tiene
aprobación requerida, está restringido a `main` y cinco variables `AZURE_*`. El detalle y las
pruebas `exec` están en `specs/009-ci-cd/evidence.md`.

Decisiones adicionales de B6:

| # | Decisión |
| --- | --- |
| D15 | `azure/login` se fija por SHA verificado de la release oficial v3.1.0 (`a641126d1b8aa4d1fa005f4f92df94a3a4c4c906`), obtenido del tag anotado en la API de GitHub; mismo criterio D3. |
| D16 | El job `deploy` valida que el output de `publish` sea un `sha256:<64 hex>` desnudo y despliega `ghcr.io/thehouse-team/thehouse-genai@<digest>`; nunca un tag. Antes de actualizar guarda la imagen activa en el resumen para rollback. |
| D17 | La verificación usa 24 intentos con 10 s de espera (≈4 min), exige revisión `Active`, `Healthy`, 1 réplica y digest exacto. No hay rollback automático: si falla, se reporta y se usa el workflow manual. |
| D18 | El rollback es un `workflow_dispatch` con validación estricta del formato de la imagen, mismo entorno protegido y misma verificación; coherente con `activeRevisionsMode: Single`. |
| D19 | No se amplía el rol ante un error de la CLI: se documenta el mensaje exacto y la acción faltante en `evidence.md` para que el operador la agregue de forma explícita. |
| D20 | Los `http.request.completed` de `/health/*` con 200 pasan a DEBUG (≈17.000 líneas/día menos); los errores siguen en INFO y las métricas no cambian. Cambio lógico separado, ya commiteado como `c13d3de`. |
| D21 | Política de costo $0: `minReplicas=0`, `maxReplicas=1` y regla HTTP explícita `concurrentRequests: '10'` con `cooldownPeriod=300` y `pollingInterval=30`. El operador aplicó `--min-replicas 0` el 2026-11-19 y el Bicep queda alineado. |
| D22 | El gating de `deploy` y `rollback` tolera 0 réplicas: revisión activa, `provisioningState=Provisioned`, `runningState` no fallido y digest exacto; `healthState=Healthy` solo con ≥1 réplica. Enums verificados en la API REST de revisiones (`Stopped`, `None`, `Failed`, `Degraded`). |
| D23 | HTTPS interno verificado el 2026-11-19 (200, payload exacto, certificado válido): `allowInsecure: false` en el Bicep y el Backend llamará a `https://ca-thehouse-genai-u2`. |
| D24 | Reaplicar el Bicep solo con el digest en ejecución, secretos del gestor de contraseñas y what-if previo; cambios esperados solo en `ingress.allowInsecure` y `template.scale`. |
| D25 | Gemini permanece en capa gratuita: Google puede usar el contenido enviado, por lo que la redacción de PII de 005 se aplica antes del envío. Derogadas las recomendaciones de proyecto de pago de 011/D-8 y deuda 004-(b). |
| D26 | `az containerapp update` usa `-o none` en `deploy` y `rollback`: el log no debe contener el JSON completo de la app (IPs de salida, nombres de variables). Las consultas previas siguen siendo puntuales con `-o tsv`. |
| D27 | La verificación exige `trafficWeight=100` en la revisión nueva y ninguna otra revisión activa con tráfico, usando `az containerapp revision list -o json` leído de disco y nunca impreso. Un peso parcial/ausente o una revisión ajena con tráfico es ESPERAR (1), nunca fatal (2), para no aprobar durante la transición. |

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

### 004-natural-language-search

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 36 archivos.
- `mypy --strict scripts/smoke_parse_search.py`: sin errores.
- `pytest`: 1021 tests aprobados, sin red (guard `block_network`), 1 warning heredado de
  `TestClient` (deuda (d)/008).
- Prueba real con `gemini-3.5-flash-lite` (delay 8 s): 27/30 en la corrida completa, 29/30
  consolidados tras reintentar ps-10 y ps-29; latencia 826/1254/1824 ms (min/mediana/max).
  El diagnóstico de ps-03 reveló el bug del parser estricto y se corrigió con un modelo de
  completion crudo más poda en guardrails.
- Rama `feature/natural-language-search`: 8 commits (B0–B7).
- Evidencia completa en `specs/004-natural-language-search/evidence.md`.

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

### 007-observability

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 32 archivos.
- `pytest`: 775 tests aprobados, sin red (guard `block_network`), 1 warning heredado de
  `TestClient` (deuda de 008).
- Rama `feature/observability`: 7 commits (B0–B6; B7 documental sin commit).
- Evidencia completa en `specs/007-observability/evidence.md`, incluida la prueba manual
  real pendiente de los endpoints internos.

### 009-ci-cd

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict) en 36 archivos.
- `mypy --strict .github/ci/revision_status.py`: sin errores (1 archivo).
- `pytest`: 1131 tests aprobados, sin red (guard `block_network`), 1 warning heredado de
  `TestClient` (deuda 008).
- `git diff --check`: limpio.
- CD verificado en CI #39 (PR #19) con la revisión `0000005`; rollback probado en
  producción el 2026-11-22 (`0000006`/`0000007`); Bicep reaplicado (revisión `0000008`).
- Rama `feature/close-ci-cd`: cambios de cierre sin commit (instrucción recibida). PRs #9 y
  #13–#19 integrados por squash a `main`.
- Evidencia completa en `specs/009-ci-cd/evidence.md`.

## Deuda y pendientes

- `GENAI_API_KEY=` y `GENAI_MODEL=` vacíos quedaban como `SecretStr('')` y `''` en lugar
  de `None`; normalizados en 011, bloque B2.
- El logging estructurado de las llamadas al proveedor (modelo, duración, `error_code`)
  se inicia en 011 con la allowlist ampliada (D-4) y se completa en 007.
- Usar contexto es-MX en los prompts reales de 004: moneda en MXN y formato de fecha y
  hora UTTT. En 003 ya se aplica (MXN, UTTT, español de México) y el prompt de 004 fija
  MXN y universidades mexicanas. El smoke test de 011 no fija esta convención porque su
  objetivo es medir latencia y calidad con datos sintéticos.
- La confirmación interactiva de `scripts/smoke_provider.py` acepta «si» en minúsculas
  porque normaliza a mayúsculas; no es un fallo, pero conviene decidir si se exige
  mayúscula estricta.
- El precio por millón de tokens del modelo de desarrollo
  (`gemini-3.5-flash-lite`) queda por anotar desde la fuente de precios, y el modelo de
  producción se decide cuando se cree el proyecto de pago (G09).
- Contratos y guardrails de parseo (004): cerrados en G08 (spec IMPLEMENTED). Los de explicación (003) están cerrados.
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
- Contract tests e integración (008–010).
- Despliegue operativo en Azure Container Apps (`ca-thehouse-genai-u2`, ingreso interno,
  solo HTTPS). La credencial de desarrollo sigue fuera del repositorio; la capa gratuita de
  Gemini se usa solo con prompts sintéticos en las pruebas manuales.

- Deuda 007-(a): métricas y presupuesto son por proceso; se pierden al reiniciar y con N
  réplicas el cupo efectivo es N× el configurado. En G10: agregación en Azure Monitor y
  cupo global en API Management o store compartido (spec aprobada).
- Deuda 007-(b): checklist de despliegue G10 — `GENAI_BUDGET_ENABLED=true`,
  `GENAI_TIMEOUT_SECONDS=6` (D18), configurar `GENAI_METRICS_KEY` y crear las alertas
  documentadas en el apéndice B de `specs/007-observability/spec.md`.
- Deuda 007-(c): el día del presupuesto es UTC-6 (México) y la cuota de Gemini se reinicia
  a medianoche hora del Pacífico; los días no coinciden exactamente. El exceso degrada a
  fallback, nunca a error.
- Deuda 007-(d): los SLOs son valores iniciales; recalibrar con datos de staging en G10.
- Deuda 007-(e): se mantiene el `StarletteDeprecationWarning` de `TestClient` con `httpx`;
  se revisa en 008. Es la misma deuda (e)/006-(d) ya registrada.
- Deuda 004-(a): confirmar con Backend la semántica de `petsAllowed` en menciones negativas
  ("sin mascotas" → `null`, nunca `false`) y sobre qué universidad se mide `maxDistanceKm`
  cuando la query nombra más de una.
- Deuda 004-(b): inestabilidad de la capa gratuita de Gemini (`PROVIDER_UNAVAILABLE` en
  ps-10 y ps-29, picos de 8 a 13 s en pruebas anteriores): pasar a la capa de pago antes de
  la demo con datos reales y recalibrar timeouts y SLOs.
- Deuda 004-(c): ampliar la tabla de alias de universidades (hoy UTTT y su nombre completo,
  más UNAM detectada por evidencia literal) con el uso real de los estudiantes.
- Deuda 004-(d): se mantiene el `StarletteDeprecationWarning` de `TestClient` con `httpx`;
  se revisa en 008. Es la misma deuda (e)/006-(d)/007-(e) ya registrada.

- Mejora opcional pendiente de decisión (G10, tras PR #9): sustituir `uvicorn[standard]`
  por `uvicorn` en `[project.dependencies]`. El extra `standard` aporta `uvloop`,
  `httptools`, `watchfiles`, `websockets`, `python-dotenv`, `pyyaml`, `click` y `h11`;
  el servicio no usa websockets ni hot-reload en producción, así que reduciría
  dependencias y superficie de ataque. No se cambió en esta corrección: el incidente se
  resolvió con locks universales y el objetivo era conservar las versiones resueltas.
  Decidir en una spec/PR posterior con su propio análisis de impacto.

### Deudas registradas al cerrar 009 (2026-11-22)

1. **Estado en memoria:** el presupuesto diario, el rate limit y las métricas viven en el
   proceso y se reinician al escalar a 0 (`minReplicas=0`). El cupo local de 400 llamadas/día
   deja de ser exacto; la cuota real la pone Gemini (500 RPD). Agrava 007-(a) y la deuda (a)
   de 005; requiere store compartido o agregación en Azure Monitor.
2. **Gemini en capa gratuita:** Google puede usar el contenido enviado para mejorar sus
   productos, por lo que la redacción de PII de 005 se aplica antes del envío. La capa
   gratuita además es inestable (deuda 004-(b): `PROVIDER_UNAVAILABLE` y picos de 8–13 s).
   El proyecto de pago con tope de gasto sigue derogado por la política de costo $0 (D25).
3. **Créditos de la suscripción de prueba de Azure:** vencen el **2026-12-02**. Después los
   servicios se pausan si no se actualiza la cuenta; hay que recordarlo antes de la demo.
4. **Estados reales de ACA no documentados en el swagger:** `ScaledToZero` y
   `RunningAtMaxScale` aparecen en producción pero no están en los enums de
   `ContainerAppsRevisions.json`; el parser los acepta y conviene vigilar futuras versiones
   de la API. `Activating` tampoco aparece en el swagger y se trata como ESPERAR.
5. **SBOM/attestations:** el aviso `Failed to create storage record / artifact-metadata:write`
   se desactivó con `create-storage-record: false` por mínimo privilegio (no se necesitan
   esos metadatos). Si en el futuro se exigen, hay que conceder `artifact-metadata:write`
   de forma explícita.
6. **Warning de `TestClient`:** `StarletteDeprecationWarning` con `httpx`, heredado y
   documentado en 003/006/007; se cierra con `008-testing` en G09.

## Próximo paso

G07 = `007-observability` y G08 = `004-natural-language-search` quedaron **IMPLEMENTED**.
G08 entregó `POST /api/v1/generative/parse-search` con autenticación y rate limit
reutilizados, moderación y PII de punta a punta, ruta de métricas propia, corpus de 30
casos y script manual opt-in; la evidencia está en
`specs/004-natural-language-search/evidence.md`.

G10 = `009-ci-cd` quedó **IMPLEMENTED** el 2026-11-22: imagen endurecida, CI/CD con GHCR y
SBOM, despliegue por digest en ACA con OIDC y rol de alcance único, verificación por
revisiones/probes con gate de tráfico exclusivo y rollback probado. Evidencia en
`specs/009-ci-cd/evidence.md`. **No hay ninguna spec ACTIVE.**

**Próximo paso: G09 = `010-integration-thehouse`**, que incluye cerrar `008-testing`
(contract tests, corpus de seguridad, cobertura y E2E en staging). Contratos y operación con
Backend, incluida la E2E de red Backend → GenAI (D11). Quedan como deuda para esa fase o
posteriores la capa de pago de Gemini con tope de gasto (deuda 2), mTLS (005-D2), la
agregación de métricas y el cupo global (deuda 1), la recalibración de SLOs (007-(d)) y el
warning de `TestClient` (deuda 6). Antes de la demo hay que recordar el vencimiento de los
créditos de Azure (deuda 3).
