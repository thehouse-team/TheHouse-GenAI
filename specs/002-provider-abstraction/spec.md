# 002-provider-abstraction — Abstracción de proveedor LLM

- **Estado:** ACTIVE
- **Depende de:** 001-foundation
- **Habilita:** 003, 004, 011
- **Fecha de alta:** 2026-11-08
- **Última revisión:** 2026-11-13

## Objetivo

Definir un puerto LLM neutral (`GenerativeAiProvider`), sus DTOs inmutables, una taxonomía
de errores, un proveedor falso determinista y una factory de selección, de modo que
application y domain nunca dependan de un SDK ni de la red. G02 es 100% offline: no se
integra ningún proveedor real.

## Contexto

Las specs 003 y 004 necesitan invocar un LLM. Sin una interfaz, prompts, SDKs y errores
del proveedor se filtrarían a application/api, dificultando pruebas, cambios de proveedor
y control de secretos. La evaluación de proveedores y el adaptador real viven en
`011-llm-provider` (G03); esta spec construye solo el contrato y el doble de test.

## Alcance

### Incluido

- Protocolo `GenerativeAiProvider` y DTOs inmutables (`GenerativeAiRequest`,
  `GenerativeAiResponse`, `GenerativeAiUsage`).
- Taxonomía de errores propia con base `ProviderError` (`ProviderTimeoutError`,
  `ProviderAuthError`, `ProviderRateLimitError`, `ProviderUnavailableError`,
  `ProviderInvalidResponseError`, `ProviderInputTooLargeError`).
- Guard central que aplica límite de entrada y timeout a cualquier implementación del
  puerto, sin que el timeout forme parte de la firma.
- `FakeProvider` determinista para tests, con fallos programables y sin acceso a red.
- Factory de selección por configuración validada; en G02 solo admite `fake`.
- Timeout obligatorio en el puerto y límite de entrada con `GENAI_MAX_INPUT_CHARS`.
- Contrato de `Settings` para proveedor, modelo, timeout y límite de entrada.

### Excluido

- Adaptador HTTP, SDK de proveedor, llamadas de red y credenciales reales (spec 011).
- Prompts de negocio, endpoints generativos, moderación, streaming, tools y embeddings.
- Reintentos automáticos o circuit breaker (se deciden en specs posteriores).
- Logging o métricas nuevos: la observabilidad pertenece a la spec 007.

## Requisitos

- **RF-01:** application y domain dependen solo del puerto, nunca de httpx ni de un SDK.
- **RF-02:** el request es inmutable, validado y acotado antes de salir del proceso.
- **RF-03:** toda invocación pasa por un guard central que aplica el timeout con
  `asyncio.wait_for` y cancela la operación interna al excederlo; el timeout no forma
  parte de la firma del puerto.
- **RF-04:** los errores se normalizan a la taxonomía propia; nunca se devuelve el
  detalle. Cada error tiene un mensaje fijo por defecto y un `code` estable, y un
  `ValidationError` de Pydantic lanzado por el proveedor se normaliza a
  `ProviderInvalidResponseError`.
- **RF-05:** el fake permite probar éxito, error y timeout sin red.
- **RF-06:** la API key se modela como `SecretStr` y no aparece en logs, `repr` ni
  respuestas.
- **RF-07:** configuración incompleta o inválida falla claramente al arrancar.
- **RF-08:** la factory no puede construir un proveedor real en G02; solo `fake`.
- **RF-09:** una entrada que exceda `GENAI_MAX_INPUT_CHARS`, medida como la suma de la
  longitud del prompt y del system prompt, se rechaza con `ProviderInputTooLargeError`
  antes de invocar al proveedor; la comparación usa solo longitudes y el mensaje no
  incluye contenido.
- **RF-10:** la factory falla con `UnsupportedProviderError`, error de configuración
  ajeno a la taxonomía `ProviderError`, si `GENAI_PROVIDER` no está definido o no es
  `fake`; `Settings` valida además el nombre del proveedor al arrancar.

## Decisiones de diseño (aprobadas 2026-11-13)

| # | Decisión | Alternativa descartada | Motivo |
| --- | --- | --- | --- |
| D-1 | Puerto, DTOs, taxonomía y guard viven en `providers/base.py`; `domain/` y `application/` no se modifican en G02 y no importan implementaciones de proveedor. | Contrato en `domain/ports.py` | El plan fija el puerto en `providers/`; la inversión estricta se revisa en 003, cuando exista `application/`. |
| D-2 | El timeout no viaja en la firma: `generate(request)`. Un guard central lo aplica a cualquier implementación. | `generate(request, *, timeout_seconds)` | Un timeout declarado por el llamante puede olvidarse; el guard lo hereda sin cambios el adaptador real de 011. |
| D-3 | El timeout se prueba por doble vía: inyección de `TimeoutError` sin espera y `hang` con timeout de 0,05 s. | Solo una de las dos | Cubre la conversión y la cancelación real sin esperas largas ni tests lentos. |
| D-4 | Los tests async usan `asyncio.run` dentro de tests síncronos; no se añade `pytest-asyncio` ni se toca `pyproject.toml`. | `pytest-asyncio` o plugin de `anyio` | Cero dependencias nuevas y CI sin cambios. |
| D-5 | `UnsupportedProviderError` deriva de `ValueError` y queda fuera de la taxonomía `ProviderError`. | Subclase de `ProviderError` | Un proveedor no soportado es un fallo de configuración o despliegue, no de una llamada. |
| D-6 | El límite de entrada mide `len(prompt) + len(system_prompt)`. | Solo `len(prompt)` | El system prompt también sale del proceso. |
| D-7 | DTOs: `prompt`, `system_prompt`, `response_format`, `temperature`, `max_output_tokens` y, en la respuesta, `text`, `usage`, `finish_reason`, `provider_model`. | DTOs mínimos | Evita romper el puerto dos veces cuando 011 necesite metadatos del proveedor. |
| D-8 | Una excepción inesperada del proveedor se normaliza a `ProviderUnavailableError` con la causa encadenada. | Relanzarla sin normalizar | El puerto garantiza que todo fallo del proveedor es un `ProviderError`. |
| D-9 | `FakeProvider` guarda las requests recibidas en memoria, solo para aserciones de test; nunca se registran. | No guardar las requests | Permite afirmar que el proveedor no fue invocado (RF-09). |
| D-10 | `pyproject.toml` no se modifica en G02. | Añadir `pytest-asyncio` | Ninguna spec aprobada autoriza dependencias nuevas. |
| D-11 | El guard vive en `providers/base.py`, junto al puerto. | `providers/guard.py` | Respeta la lista de archivos previstos del plan. |
| D-12 | G02 no añade logging en el guard ni amplía la allowlist de campos del logging JSON. | Loggear `provider` y `error_code` en 002 | La observabilidad pertenece a la spec 007. |
| D-13 | `README.md` se corrige al activar la spec para no contradecir `memoria.md`. | Corrección al cerrar la spec | Consistencia documental inmediata. |
| D-14 | `Settings.genai_provider` es `Literal["fake"]` opcional (`None` si no se define) y la factory revalida el nombre: doble barrera. | `str` libre con la factory como única puerta | La configuración inválida falla al arrancar (RF-07) y la factory nunca construye un proveedor real (RF-08). |
| D-15 | Estas decisiones se documentan en la spec activa; no hay plan externo al repositorio. | Plan fuera del repositorio | El SDD del repositorio es la única fuente de verdad. |

### Correcciones obligatorias al diseño

1. El guard de red de los tests **no** sustituye `socket.socket` ni bloquea la creación de
   sockets: `asyncio.run` usa `socketpair`, que en Windows conecta a `127.0.0.1`. Solo se
   bloquean `socket.socket.connect`, `socket.socket.connect_ex` y
   `socket.create_connection` cuando el destino no es loopback (`127.0.0.1`, `::1`,
   `localhost`), con un mensaje claro.
2. `"fake "` no es un caso de proveedor rechazado: `Settings` normaliza el nombre
   (minúsculas y sin espacios) y lo acepta.
3. Un `pydantic.ValidationError` lanzado por el proveedor se normaliza a
   `ProviderInvalidResponseError`, antes del `except Exception` genérico.
4. Cada error de la taxonomía tiene un mensaje fijo por defecto, de modo que `str(exc)`
   nunca es vacío ni contiene detalle del proveedor.

## Criterios de aceptación

- [ ] Puerto y DTOs aprobados, tipados en modo estricto.
- [ ] Test de frontera: application/domain no importan httpx ni SDKs de proveedor.
- [ ] Timeout verificado de forma determinista con el fake; el puerto expone
      `ProviderTimeoutError`.
- [ ] Errores normalizados a la taxonomía propia (`ProviderAuthError`,
      `ProviderRateLimitError`, `ProviderUnavailableError`,
      `ProviderInvalidResponseError`) sin filtrar detalles internos.
- [ ] `FakeProvider` cubre éxito, error y timeout.
- [ ] La factory rechaza proveedores distintos de `fake` en G02.
- [ ] Entrada que excede `GENAI_MAX_INPUT_CHARS` produce `ProviderInputTooLargeError`
      antes de invocar el puerto.
- [ ] Configuración incompleta o inválida falla al iniciar.

## Seguridad y privacidad

- No registrar prompts ni respuestas completas por defecto; solo metadatos.
- Redactar cualquier clave o cabecera sensible en logs y excepciones.
- Validar tamaño y campos permitidos antes de invocar el proveedor.
- Sin reintentos en esta spec para no amplificar coste ni latencia.
- Sin red, sin credenciales y sin datos reales en fixtures.

## Fuera de esta spec

Esta spec está `ACTIVE` desde 2026-11-13. Su alcance es el puerto, los DTOs, la
taxonomía de errores, el guard central, el fake, la factory y la configuración validada.
No incluye adaptadores reales, llamadas de red, endpoints generativos, prompts de
negocio ni credenciales.
