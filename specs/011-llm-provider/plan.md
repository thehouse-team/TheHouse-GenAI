# Plan — 011-llm-provider Proveedor LLM real

- **Estado:** ACTIVE
- **Depende de:** 002-provider-abstraction
- **Fecha de activación:** 2026-11-15

## Enfoque técnico

1. Evaluar antes de integrar: la matriz se cierra antes de escribir código de vendor.
2. Un único adaptador elegido, detrás de `GenerativeAiProvider`; el vendor no aparece en
   application ni domain.
3. El cliente HTTP se inyecta y se construye con timeout; las pruebas usan un doble.
4. La respuesta del vendor se valida con Pydantic y se normaliza al DTO interno.
5. Los errores se mapean en el borde del adaptador; el resto del servicio no conoce el
   vendor.
6. El identificador del modelo se registra solo en logs y metadatos internos; la respuesta
   de la API no lo expone.
7. El smoke test es un script opt-in, con interruptor explícito, que CI nunca ejecuta.

## Pasos previstos

1. Recopilar precio, capa gratuita, latencia, JSON estructurado, español y soporte
   Python de los tres candidatos, con fuentes citadas.
2. Redactar la matriz comparativa y el documento de decisión.
3. Implementar el adaptador del proveedor elegido sobre `providers/base.py`.
4. Añadir el proveedor a la factory y a la configuración validada.
5. Implementar la normalización de respuesta y el mapeo de errores.
6. Añadir tests de contrato y de errores con dobles, sin red.
7. Escribir el script de smoke test manual y documentar su uso.
8. Actualizar SDD y evidencia al cerrar.

## Archivos previstos

- `specs/011-llm-provider/evaluation.md`
- `specs/011-llm-provider/decision.md`
- `src/thehouse_genai/providers/gemini.py`
- `src/thehouse_genai/providers/factory.py`
- `src/thehouse_genai/infrastructure/config.py`
- `src/thehouse_genai/infrastructure/logging.py`
- `scripts/smoke_provider.py`
- `tests/test_provider_adapter.py`
- `tests/test_smoke_script.py`

> Enmienda del 2026-11-15, con la spec activa: el archivo del adaptador se fija en
> `providers/gemini.py`, en coherencia con `providers/fake.py` y
> `providers/factory.py`, en lugar del marcador `<vendor>_provider.py`. Se añaden
> `infrastructure/logging.py`, porque la allowlist del logging JSON debe admitir
> `provider`, `provider_model`, `error_code`, `duration_ms`, `prompt_chars` y
> `completion_chars` para registrar el modelo interno sin registrar contenido, y
> `tests/test_smoke_script.py`, que verifica que el script manual nunca lo ejecuta
> CI.

## Bloques de ejecución

Cada bloque deja el repositorio verde y se cierra con un commit.

| # | Bloque | Contenido | Gates |
| --- | --- | --- | --- |
| B1 | Activación, evaluación y decisión | Cabeceras de la spec, `memoria.md`, `evaluation.md`, `decision.md`, `README.md` | `ruff`, `mypy`, `pytest`, `git diff --check` |
| B2 | Configuración validada | `infrastructure/config.py`, `tests/test_config.py`, `.env.example` | `ruff`, `mypy`, `pytest` |
| B3 | Adaptador: request y respuesta | `providers/gemini.py`, `tests/test_provider_adapter.py` | `ruff`, `mypy`, `pytest` |
| B4 | Adaptador: errores, timeout y logging | `providers/gemini.py`, `infrastructure/logging.py`, `tests/test_provider_adapter.py` | `ruff`, `mypy`, `pytest` |
| B5 | Factory | `providers/factory.py`, `tests/test_provider_factory.py` | `ruff`, `mypy`, `pytest` |
| B6 | Frontera de imports | `tests/test_import_boundaries.py` | `ruff`, `mypy`, `pytest` |
| B7 | Smoke test manual | `scripts/smoke_provider.py`, `tests/test_smoke_script.py` | `ruff`, `mypy`, `pytest` y `mypy --strict scripts/smoke_provider.py` |
| B8 | Ejecución del smoke test | `evidence.md`, `evaluation.md` | `ruff`, `mypy`, `pytest` |
| B9 | Cierre | `checklist.md`, `evidence.md`, `memoria.md`, `README.md` | `ruff`, `mypy`, `pytest` |

## Estrategia de pruebas

- Contrato del adaptador con doble HTTP: éxito, error y timeout.
- Parseo de la respuesta del vendor a `GenerativeAiResponse`.
- Mapeo de 401/429/5xx del vendor a la taxonomía propia sin filtrar su cuerpo.
- Frontera de imports: application y domain no importan el SDK del vendor.
- Test que verifica que la suite no abre conexiones.
- Test que verifica que el identificador del modelo no aparece en el payload de respuesta.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Vendor filtration al dominio | Adaptador delgado + test de frontera de imports. |
| Fuga de credencial | `SecretStr`, redacción centralizada y tests de representación. |
| Exposición del modelo interno al cliente | Solo logs y metadatos internos; test que lo verifica. |
| Coste inesperado | Límite de entrada, timeout y sin reintentos automáticos. |
| Tests dependientes de red | Dobles obligatorios y smoke test fuera de CI. |
| Cambio de precio o de modelo | Revisión periódica de la matriz y del documento de decisión. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
