# Plan — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED
- **Depende de:** 001-foundation

## Enfoque técnico

1. Aplicar ports & adapters: el puerto vive en `providers/base.py` y toda implementación
   lo satisface.
2. El puerto se consumirá por dependency injection cuando exista la capa application;
   G02 no crea código en `application/`.
3. Definir errores propios (`ProviderTimeoutError`, `ProviderAuthError`,
   `ProviderInputTooLargeError`, etc.) sin heredar de ningún SDK.
4. Mantener el puerto delgado: validar, delegar, normalizar resultado y error.
5. El fake devuelve respuestas fijas y permite programar fallos y timeouts.
6. La factory resuelve el proveedor desde `Settings`; en G02 solo `fake` es válido.
7. Ninguna ruta de código de G02 abre un socket.

## Pasos previstos

1. Definir DTOs, protocolo `GenerativeAiProvider` y taxonomía de errores.
2. Extender `Settings` para proveedor, modelo, timeout y límite de entrada.
3. Implementar `FakeProvider` determinista y sus helpers de test.
4. Implementar la factory con validación estricta del proveedor soportado.
5. Añadir tests de contrato, timeout, errores, límite de entrada y frontera de imports.
6. Actualizar SDD y evidencia al cerrar.

## Archivos previstos

- `src/thehouse_genai/providers/base.py`
- `src/thehouse_genai/providers/fake.py`
- `src/thehouse_genai/providers/factory.py`
- `src/thehouse_genai/infrastructure/config.py`
- `tests/test_providers.py`

## Estrategia de pruebas

- Contrato del puerto con `FakeProvider`: éxito, error, timeout y respuesta inválida.
- Timeout determinista programado en el fake, sin esperas reales ni red.
- Mapeo de errores a la taxonomía propia sin texto del proveedor.
- Entrada que excede `GENAI_MAX_INPUT_CHARS` produce `ProviderInputTooLargeError` antes
  de invocar el puerto.
- Configuración incompleta falla con mensaje claro.
- Frontera de imports: application y domain no importan httpx ni SDKs.
- Test que garantiza que la suite no abre conexiones de red.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Acoplamiento oculto a un vendor | Puerto propio + test de frontera de imports. |
| Fuga de secretos en errores | Taxonomía segura y redacción centralizada. |
| Tests dependientes de red | `FakeProvider` obligatorio en CI. |
| Timeout mal calibrado | Validación de rango y timeout determinista con el fake. |
| Adelanto del proveedor real | La factory rechaza todo proveedor distinto de `fake`. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
