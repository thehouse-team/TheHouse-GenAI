# Plan — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction

## Enfoque técnico

1. Definir un schema cerrado de filtros con `extra="forbid"`.
2. Pedir al proveedor JSON estricto y validar con Pydantic.
3. Normalizar solo valores permitidos; lo demás queda sin resolver.
4. Rechazar cualquier campo de propiedad o resultado de búsqueda.
5. Probar el contrato con fake provider y consultas adversariales.

## Pasos previstos

1. Aprobar schema de filtros y semántica de aclaración.
2. Implementar validaciones y allowlists.
3. Implementar prompt y caso de uso de parseo.
4. Implementar endpoint autenticado y errores seguros.
5. Añadir pruebas de ejemplo, ambigüedad e inyección.
6. Actualizar SDD y evidencia.

## Archivos previstos

- `src/thehouse_genai/domain/search_filters.py`
- `src/thehouse_genai/application/parse_search.py`
- `src/thehouse_genai/api/routes/generative.py`
- `tests/test_parse_search.py`

## Estrategia de pruebas

- Consulta de ejemplo produce filtros correctos.
- Respuesta sin campos de propiedad, incluso con inyección.
- Consulta ambigua requiere aclaración.
- Entrada vacía/oversized produce 422.
- Error/timeout del proveedor produce 502 seguro.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| El modelo inventa filtros | Schema estricto y allowlist de campos/servicios. |
| El modelo devuelve propiedades | Validador de salida que rechaza cualquier campo extra. |
| Consulta ambigua resuelta por suposición | `unresolved_terms` y aclaración obligatoria. |
| Abuso por consultas enormes | Límite de caracteres y tamaño de request. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
