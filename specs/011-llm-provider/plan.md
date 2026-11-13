# Plan — 011-llm-provider Proveedor LLM real

- **Estado:** PLANNED
- **Depende de:** 002-provider-abstraction

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
- `src/thehouse_genai/providers/<vendor>_provider.py`
- `src/thehouse_genai/providers/factory.py`
- `src/thehouse_genai/infrastructure/config.py`
- `scripts/smoke_provider.py`
- `tests/test_provider_adapter.py`

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
