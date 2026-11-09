# Plan — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED
- **Depende de:** 001-foundation

## Enfoque técnico

1. Aplicar ports & adapters: el puerto vive en `providers/base.py` y los adaptadores lo implementan.
2. Inyectar el proveedor en los casos de uso; nada de singletons globales.
3. Definir errores propios (`ProviderTimeout`, `ProviderAuthError`, etc.) sin heredar del SDK.
4. Mantener el adaptador delgado: serializar, llamar, validar respuesta, mapear errores.
5. El fake devuelve respuestas fijas y permite programar fallos.

## Pasos previstos

1. Definir DTOs, puerto y taxonomía de errores.
2. Extender `Settings` para selección y validación del proveedor.
3. Implementar adaptador httpx con timeout y cliente inyectable.
4. Implementar fake determinista y helpers de test.
5. Conectar el proveedor por dependency injection en la futura capa application.
6. Añadir tests de contrato, timeout, errores y frontera de imports.
7. Actualizar SDD y evidencia al cerrar.

## Archivos previstos

- `src/thehouse_genai/providers/base.py`
- `src/thehouse_genai/providers/httpx_provider.py`
- `src/thehouse_genai/providers/fake.py`
- `src/thehouse_genai/infrastructure/config.py`
- `tests/test_providers.py`

## Estrategia de pruebas

- Contrato del puerto con fake: éxito, error, timeout y respuesta inválida.
- Timeout real simulado con `httpx.MockTransport`.
- Mapeo de errores sin texto del proveedor.
- Configuración incompleta falla con mensaje claro.
- Frontera de imports para application/domain.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Acoplamiento oculto a un vendor | Puerto propio + test de frontera de imports. |
| Fuga de secretos en errores | Taxonomía segura y redacción centralizada. |
| Tests dependientes de red | Fake provider obligatorio en CI. |
| Timeout mal calibrado | Validación de rango y pruebas con transporte lento simulado. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
