# Plan — 006-moderation Moderación de contenido

- **Estado:** PLANNED
- **Depende de:** 002-provider-abstraction, 005-security

## Enfoque técnico

1. Definir política y taxonomía antes de elegir tecnología.
2. Crear puerto `ModerationProvider` y fake para tests.
3. Integrar moderación en el pipeline generativo antes/después del LLM.
4. Registrar solo decisión, categoría, versión y request ID.

## Pasos previstos

1. Redactar y aprobar política de moderación.
2. Definir puerto, DTOs y taxonomía.
3. Implementar fake y pipeline de moderación.
4. Integrar en casos de uso generativos.
5. Añadir pruebas y métricas de decisión.
6. Actualizar SDD y evidencia.

## Archivos previstos

- `src/thehouse_genai/domain/moderation.py`
- `src/thehouse_genai/providers/moderation.py`
- `tests/test_moderation.py`

## Estrategia de pruebas

- Contenido permitido continúa el flujo.
- Contenido bloqueado no se responde.
- Error/timeout del moderador aplica fail-closed.
- Logs solo contienen metadatos.
- Pruebas de categorías y falsos positivos.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Sesgo o falsos positivos | Ruta de revisión y métricas de bloqueo. |
| Moderador externo caído | Política fail-closed y timeout. |
| Fuga de contenido en logs | Auditoría solo con metadatos. |
| Categorías ambiguas | Política versionada y ejemplos. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
