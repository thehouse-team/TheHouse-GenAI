# Memoria del proyecto — TheHouse GenAI

Última actualización: 2026-11-15

## Identidad

Repositorio independiente para IA generativa de TheHouse. Recibe contexto calculado por
TheHouse Backend y produce explicaciones o filtros. No sustituye al Backend, no calcula
Smart Match, no consulta propiedades y no contiene Mobile.

## Estado de specs

| Spec | Estado | Alcance |
| --- | --- | --- |
| 001-foundation | IMPLEMENTED | Servicio mínimo, health, config, seguridad base, tests, CI |
| 002-provider-abstraction | IMPLEMENTED | Puerto `GenerativeAiProvider`, DTOs, errores, fake y factory (offline) |
| 003-smart-match-explanation | PLANNED | Explicación de match sin alterar hechos, con auth mínima de servicio |
| 004-natural-language-search | PLANNED | Parseo de búsqueda a filtros, nunca propiedades |
| 005-security | PLANNED | Autenticación de servicio endurecida, PII, prompt injection |
| 006-moderation | PLANNED | Política y moderación de contenido |
| 007-observability | PLANNED | Métricas, trazas, SLOs y alertas |
| 008-testing | PLANNED | Estrategia completa y contract tests (transversal, cierra en G09) |
| 009-ci-cd | PLANNED | Pipeline completo y despliegue futuro |
| 010-integration-thehouse | PLANNED | Contratos y operación con Backend |
| 011-llm-provider | ACTIVE | Evaluación de proveedores y adaptador real detrás del puerto |

## Mapeo de fases

| Fase | Spec | Contenido |
| --- | --- | --- |
| G01 | 001-foundation | Servicio base, health, configuración, CI (IMPLEMENTED) |
| G02 | 002-provider-abstraction | Puerto LLM, DTOs, errores, fake y factory, 100% offline (IMPLEMENTED) |
| G03 | 011-llm-provider | Evaluación de proveedores y adaptador real |
| G04 | 003-smart-match-explanation | Endpoint explain-match con auth mínima de servicio |
| G05 | 005-security | Endurecimiento de seguridad, PII, prompt injection |
| G06 | 006-moderation | Moderación de contenido |
| G07 | 007-observability | Observabilidad, métricas y SLOs |
| G08 | 004-natural-language-search | Endpoint parse-search con auth endurecida |
| G09 | 010-integration-thehouse | Integración con Backend; cierra 008-testing |
| G10 | 009-ci-cd | Pipeline completo y despliegue |

`008-testing` es transversal: sus entregables (contract tests, corpus de seguridad,
cobertura) se acumulan en cada fase y la spec se cierra en G09, junto con
`010-integration-thehouse`, que es la que exige contract tests y E2E en staging.

## Spec activa

`011-llm-provider` (G03) está `ACTIVE` desde 2026-11-15 en la rama
`feature/llm-provider`. Su plan está aprobado y la decisión de proveedor quedó
documentada en `specs/011-llm-provider/decision.md`, con la matriz comparativa en
`specs/011-llm-provider/evaluation.md`. `002-provider-abstraction` permanece
`IMPLEMENTED` y el resto de specs, `PLANNED`. Solo una spec puede estar `ACTIVE` a
la vez.

La spec no se cierra como `IMPLEMENTED` hasta que el smoke test manual se haya
ejecutado con una credencial real y su resultado quede registrado en
`specs/011-llm-provider/evidence.md`.

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

## Deuda y pendientes

- `GENAI_API_KEY=` y `GENAI_MODEL=` vacíos quedaban como `SecretStr('')` y `''` en lugar
  de `None`; normalizados en 011, bloque B2.
- `StarletteDeprecationWarning` de `TestClient` con `httpx`; se revisa en 008.
- El logging estructurado de las llamadas al proveedor (modelo, duración, `error_code`)
  se inicia en 011 con la allowlist ampliada (D-4) y se completa en 007.
- Construir el adaptador real detrás del puerto (011, en curso): evaluación y decisión
  cerradas en el bloque B1.
- El smoke test manual (`scripts/smoke_provider.py`) aún no se ha escrito ni ejecutado:
  su ejecución con credencial real es requisito para cerrar 011 (D-12).
- Contratos y guardrails de explicación (003) y parseo (004).
- Auth mínima de servicio en 003; endurecimiento, PII y prompt injection en 005.
- Moderación, observabilidad avanzada, contract tests e integración (006–010).
- No hay despliegue ni credenciales reales configuradas.

## Próximo paso

G03 = `011-llm-provider`, en curso: la evaluación y la decisión de proveedor están
cerradas (bloque B1). Continúa el adaptador `GeminiProvider` detrás del puerto
`GenerativeAiProvider`, la configuración validada, el registro en la factory, el test
de fronteras y el script de smoke test manual, por bloques y dejando el repositorio
verde. `003-smart-match-explanation` permanece `PLANNED` hasta el cierre de 011.
