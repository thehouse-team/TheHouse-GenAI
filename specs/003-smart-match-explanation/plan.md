# Plan — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** ACTIVE
- **Depende de:** 001-foundation, 002-provider-abstraction, 011-llm-provider
- **Rama:** `feature/smart-match-explanation`

## Enfoque técnico

1. Definir schemas Pydantic de entrada/salida antes de cualquier prompt: camelCase en el
   alambre con aliases sobre modelos Python snake_case y `extra="forbid"` (D1).
2. Construir un contexto serializado solo con campos allowlist, escapando delimitadores;
   los datos de entrada se tratan como no confiables.
3. Solicitar `{"explanation": "..."}` con `response_format="json"` y prompt versionado
   `explain_match_v3` (v1 y v2 históricas); normalizar espacios antes de validar (D17)
   y aplicar guardrails deterministas, incluido `MALFORMED_TEXT` (D14).
4. Extraer y normalizar a decimal todos los números de la salida y comprobar que
   pertenezcan al input; el porcentaje, si aparece, debe igualar `matchScore` (D3, D13).
5. Usar `FakeProvider` para probar guardrails sin depender del modelo ni de la red.
6. Ante fallo del proveedor, timeout o rechazo de validación, responder **200** con
   `generated=false` y plantilla neutra; **no se mapea a 502** (D4). El proveedor no
   configurado degrada con log `ERROR` y su readiness se decide en 007 (D5).
7. La autenticación es una dependencia de FastAPI con `hmac.compare_digest`; falla
   cerrado con 401 antes de tocar el proveedor.
8. El factory construye el proveedor al arrancar y se inyecta por `app.state` mediante
   una dependencia de FastAPI; `application/` solo importa `providers.base`.

## Contrato aprobado

- Request: `{matchScore, locale, university, property {title, price, currency,
  distanceKm, services[]}, preferences {budgetMax, currency, maxDistanceKm,
  essentialServices[]}}`. `locale` solo `es-MX`; `university` es `str`; `price` y
  `budgetMax` son `Decimal` ≥ 0 con máximo 2 decimales; `property.currency !=
  preferences.currency` → 422 (D6, D7, D9, ajuste 4).
- Response: `{explanation, generated, promptVersion}`; sin `facts_used`, sin score como
  campo y sin metadatos del proveedor (D2; detalle en RF-11).
- Servicios: rechazar solo caracteres de control y longitud > 40; delimitadores como
  `<untrusted_data>` se escapan en `to_context()`, no se rechazan (ajuste 5).
- Regla 4 del system prompt: «no lo completes ni lo deduzcas» (ajuste 1).
- Plantilla de fallback: coincidencia con las preferencias del estudiante, no con la
  universidad, sin «No se pudo generar» (ajuste 3).

## Pasos previstos

1. Aprobar contrato y allowlist de hechos (hecho en B1).
2. Implementar schemas y validaciones de entrada (B3).
3. Implementar constructor de contexto y prompt con delimitadores (B5).
4. Implementar validador de salida, sin `facts_used` expuesto (B5).
5. Implementar la dependencia de autenticación de servicio (`X-Service-Key`, credencial
   en `Settings` como `SecretStr`, comparación en tiempo constante) (B2 + B4).
6. Crear el caso de uso y el endpoint protegido por esa dependencia (B5 + B6).
7. Añadir pruebas de fidelidad, límites e inyección (B7).
8. Actualizar SDD y evidencia (B8).

## Bloques de implementación

| Bloque | Contenido | Estado |
| --- | --- | --- |
| B1 | Activación y documentación (sin código runtime). | Completado |
| B2 | `service_key` en `Settings`, `.env.example` y tests de config. | Completado |
| B3 | Modelos de dominio e invariantes. | Completado |
| B4 | Dependencia de autenticación `X-Service-Key`. | Completado |
| B5 | Prompt `explain_match_v1`, caso de uso, validación y fallback. | Completado |
| B6 | Factory en arranque, inyección por `app.state` y endpoint. | Completado |
| B7 | Prompt v2, `MALFORMED_TEXT`, logger `httpx` y respuestas reales. | Completado |
| B7b | Normalización de espacios, prompt v3 y respuestas reales v2. | En curso |
| B8 | Cierre SDD, evidencia y PR. | Pendiente |

Cada bloque deja `ruff check .`, `mypy src` y `pytest` en verde. B1 se commita; B2 no se
commitea y no se avanza a B3 sin revisión.

## Archivos previstos

- `src/thehouse_genai/domain/match_explanation.py`
- `src/thehouse_genai/application/explain_match.py`
- `src/thehouse_genai/api/routes/generative.py`
- `src/thehouse_genai/api/auth.py`
- `src/thehouse_genai/infrastructure/config.py`
- `src/thehouse_genai/infrastructure/logging.py`
- `tests/test_config.py` (ampliar)
- `tests/test_domain_match_explanation.py`
- `tests/test_auth.py`
- `tests/test_explain_match.py`
- `tests/test_generative_api.py`

## Estrategia de pruebas

- Fixture canónica produce explicación válida y breve.
- Datos faltantes, score inválido, `locale` no `es-MX` y monedas dispares producen 422.
- `price`/`budgetMax` con más de 2 decimales producen 422.
- Salida con número, porcentaje o servicio inventado se rechaza y degrada a fallback.
- Intento de prompt injection no altera hechos ni reglas; delimitadores se escapan.
- Timeout/error del proveedor y salida rechazada producen **200** con
  `generated=false`, nunca 502.
- Sin `X-Service-Key` y con `X-Service-Key` incorrecto se responde 401 con el sobre
  estándar y sin filtrar detalles.
- `provider_model` y la credencial no aparecen en la respuesta ni en logs.

## Decisiones D1–D17 y ajustes

Ver la tabla completa en `spec.md`, sección «Decisiones aprobadas». Resumen: D1 camelCase
con alias; D2 sin `facts_used`; D3 porcentaje validado; D4 200 + `generated=false` sin
502; D5 degradar con log `ERROR` y readiness en 007; D6 solo `es-MX`; D7 `university`
como `str`; D8 `GENAI_SERVICE_KEY`; D9 422 por monedas dispares; D10 medir tamaño del
prompt en B5; D11 gobernanza en B1; D12 vocabulario corto de servicios en `domain`; D13
normalización a decimal. Ajustes 1–5: redacción de la regla 4 del system prompt, rama
`feature/smart-match-explanation`, plantilla de fallback neutra, `Decimal` para
precios y validación laxa de servicios con delimitadores escapados. B7 añade D14
(`MALFORMED_TEXT` acotado para palabras pegadas), D15 (prompt v2 con el feedback real de
Gemini; v1 queda histórica), D16 (logger `httpx` en WARNING) y D17 (normalizar espacios
en vez de rechazar, prompt v3 sin saludos y con `%`, sin «por ciento»).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Alucinación de servicios o precios | Validación determinista contra hechos de entrada. |
| El modelo recalcula el score | Score como hecho autoritativo, porcentaje validado y salida sin campo de score. |
| Prompt injection en descripciones | Delimitadores escapados, allowlist y validación de salida. |
| Falsos rechazos por formato numérico | Normalización a decimal (D13); ante duda, fallback seguro. |
| Palabras pegadas (`delpresupuesto`) | Detector acotado con allowlist (D14); fallback `MALFORMED_TEXT`. |
| Espacios faltantes junto a puntuación | Normalización determinista previa (D17); nunca toca decimales ni miles. |
| `GENAI_MAX_INPUT_CHARS` insuficiente | Medir system prompt + contexto en B5 (D10). |
| Exposición de PII | Contrato mínimo y filtro previo a GenAI. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
