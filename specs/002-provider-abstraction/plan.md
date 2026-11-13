# Plan — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** IMPLEMENTED
- **Depende de:** 001-foundation

## Enfoque técnico

1. Aplicar ports & adapters: el puerto vive en `providers/base.py` y toda implementación
   lo satisface.
2. El puerto se consumirá por dependency injection cuando exista la capa application;
   G02 no crea código en `application/` ni en `domain/`.
3. Definir errores propios con base `ProviderError` (`ProviderTimeoutError`,
   `ProviderAuthError`, `ProviderRateLimitError`, `ProviderUnavailableError`,
   `ProviderInvalidResponseError`, `ProviderInputTooLargeError`), sin heredar de ningún
   SDK, cada uno con mensaje fijo por defecto y `code` estable.
4. Mantener el puerto delgado: validar, delegar, normalizar resultado y error. Un
   `ValidationError` de Pydantic del proveedor se normaliza a
   `ProviderInvalidResponseError` antes del `except Exception` genérico, y cualquier
   excepción inesperada a `ProviderUnavailableError` con la causa encadenada.
5. El guard central (`GuardedProvider`, en `providers/base.py`) aplica el límite de
   entrada y el timeout: el timeout no forma parte de la firma del puerto y se aplica
   con `asyncio.wait_for`, que cancela la operación interna al excederlo. El límite
   compara `len(prompt) + len(system_prompt)` contra `GENAI_MAX_INPUT_CHARS` y se
   comprueba antes de invocar al proveedor.
6. El fake devuelve respuestas fijas y permite programar fallos y timeouts: éxito con
   texto fijo, error programado, `hang` para el timeout real y llamadas registradas en
   memoria solo para aserciones de test.
7. La factory resuelve el proveedor desde `Settings`; en G02 solo `fake` es válido y
   cualquier otro valor o la ausencia de valor producen `UnsupportedProviderError`,
   error de configuración ajeno a la taxonomía `ProviderError`.
8. `Settings.genai_provider` se declara `Literal["fake"] | None`, de modo que un
   proveedor inválido falla al arrancar; la factory revalida el nombre como segunda
   barrera.
9. Ninguna ruta de código de G02 abre un socket.
10. G02 no añade logging ni amplía la allowlist de campos del logging JSON.

## Decisiones que condicionan el plan

Las decisiones completas, con alternativas y motivos, están en `spec.md` (D-1 a D-15).
Sus consecuencias sobre este plan son:

| # | Consecuencia en el plan |
| --- | --- |
| D-1 | Todo el contrato vive en `providers/`; `domain/` y `application/` no se tocan y el test de frontera lo verifica. |
| D-2 | La firma del puerto es `generate(request)`; el timeout lo aplica el guard, no el llamante. |
| D-3 | El test de timeout tiene dos casos: inyección de `TimeoutError` sin espera y `hang` con timeout de 0,05 s. |
| D-4 | Los tests async se ejecutan con `asyncio.run` dentro de tests síncronos; `pyproject.toml` no cambia. |
| D-5 | `UnsupportedProviderError` deriva de `ValueError` y se documenta aparte de la taxonomía. |
| D-6 | La longitud medida es la suma de prompt y system prompt. |
| D-7 | Los DTOs se fijan aquí y no se amplían sin cambio de spec. |
| D-8 | La normalización de excepciones desconocidas vive en el guard. |
| D-9 | El fake expone las llamadas recibidas para aserciones; nunca se registran. |
| D-10 | Sin dependencias nuevas. |
| D-11 | El guard se implementa en `providers/base.py`. |
| D-12 | Sin logging nuevo en G02. |
| D-13 | `README.md` se actualiza en la activación. |
| D-14 | `Settings` limita el nombre del proveedor y la factory lo revalida. |
| D-15 | No hay plan fuera del repositorio. |

## Pasos previstos

1. Definir DTOs, protocolo `GenerativeAiProvider`, taxonomía de errores y guard central.
2. Extender `Settings` para proveedor, modelo, timeout y límite de entrada.
3. Implementar `FakeProvider` determinista y sus helpers de test.
4. Implementar la factory con validación estricta del proveedor soportado.
5. Añadir tests de contrato, timeout, errores, límite de entrada y frontera de imports.
6. Actualizar SDD y evidencia al cerrar.

## Archivos previstos

- `src/thehouse_genai/providers/__init__.py` (docstrings del paquete, sin cambios de
  comportamiento)
- `src/thehouse_genai/providers/base.py` (puerto, DTOs, taxonomía de errores y guard
  central)
- `src/thehouse_genai/providers/fake.py` (doble de test determinista)
- `src/thehouse_genai/providers/factory.py` (selección de proveedor y conjunto de
  proveedores soportados)
- `src/thehouse_genai/infrastructure/config.py` (contrato de `Settings` del proveedor)
- `.env.example` (comentario y valor de `GENAI_PROVIDER`)
- `tests/conftest.py` (guard de red y fixtures)
- `tests/test_config.py` (validación de la configuración del proveedor)
- `tests/test_providers.py` (puerto, DTOs, errores, guard y fake)
- `tests/test_provider_factory.py` (factory)
- `tests/test_import_boundaries.py` (frontera de imports y suite offline)

## Estrategia de pruebas

- Contrato del puerto con `FakeProvider`: éxito, error, timeout y respuesta inválida.
- Timeout determinista por doble vía: inyección de `TimeoutError` sin espera y `hang`
  con timeout de 0,05 s, que ejercita la cancelación real de `asyncio.wait_for`.
- Mapeo de errores a la taxonomía propia sin texto del proveedor; un
  `ValidationError` de Pydantic del proveedor se normaliza a
  `ProviderInvalidResponseError`.
- Cada error de la taxonomía tiene mensaje fijo no vacío y `code` estable.
- Entrada que excede `GENAI_MAX_INPUT_CHARS` produce `ProviderInputTooLargeError` antes
  de invocar al puerto y el fake registra cero llamadas.
- Configuración incompleta o inválida falla con mensaje claro; el nombre del proveedor se
  normaliza y `"fake "` se acepta.
- Frontera de imports: `domain/` y `application/` no importan `httpx` ni SDKs ni
  implementaciones de proveedor, y ningún módulo de `src/` importa clientes HTTP o SDKs
  de proveedor en G02.
- Test que garantiza que la suite no usa red: el guard de tests bloquea
  `socket.socket.connect`, `socket.socket.connect_ex` y `socket.create_connection`
  hacia destinos que no sean loopback, con mensaje claro. No se sustituye
  `socket.socket` ni se bloquea la creación de sockets, porque `asyncio.run` usa
  `socketpair`, que en Windows conecta a `127.0.0.1`.
- Tests async con `asyncio.run` dentro de tests síncronos; no se añade `pytest-asyncio`
  ni se modifica `pyproject.toml`.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Acoplamiento oculto a un vendor | Puerto propio + test de frontera de imports. |
| Fuga de secretos en errores | Taxonomía con mensajes fijos y `code` estable; sin detalle del proveedor. |
| Tests dependientes de red | `FakeProvider` obligatorio en CI y guard de red que bloquea destinos no loopback. |
| Timeout mal calibrado | Validación de rango en `Settings` y timeout determinista con el fake. |
| Adelanto del proveedor real | `Settings` limita el nombre a `fake` y la factory rechaza cualquier otro valor. |
| Falsos verdes en el test de frontera | El test recorre el AST de todo `src/`, no solo de `domain/` y `application/`. |
| Ambigüedad del límite de entrada | Se mide `prompt + system_prompt` y queda escrito en la spec. |
| Fuga del detalle del proveedor | Errores con mensaje fijo; el texto del vendor nunca entra en la excepción ni en el log. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
