# Plan — 006-moderation Moderación de contenido

- **Estado:** ACTIVE
- **Depende de:** 002-provider-abstraction, 005-security, 011-llm-provider
- **Plan aprobado:** 2026-11-18
- **Alcance aprobado:** A (salida generativa + `safetySettings`)

## Enfoque técnico

1. Política y taxonomía antes que tecnología: `moderation_v1` en `domain/`, sin
   dependencias nuevas y sin importar proveedores.
2. Puerto `ModerationProvider` con DTOs inmutables, taxonomía de errores, guard, fake y
   un moderador local determinista que delega en la política.
3. Inyectar el puerto en `ExplainMatch` desde la capa HTTP; moderar la salida validada
   antes de responder. Toda decisión adversa degrada al fallback de 003.
4. Añadir `safetySettings` al payload de Gemini como refuerzo del proveedor, sin llamadas
   extra.
5. Registrar solo decisión, categoría, motivo y versión de política; nunca contenido.

## Bloques

| Bloque | Contenido | Archivos | Tests |
| --- | --- | --- | --- |
| B1 | Activación, spec y plan revisados, RF-02, decisiones A1–A7, README y deuda (f) | `memoria.md`, `specs/006-moderation/*`, `specs/003-smart-match-explanation/spec.md`, `README.md` | — (solo docs; gates en verde) |
| B2 | Política `moderation_v1`: categorías, códigos de motivo, detectores de correo, teléfono (10 dígitos, `+52` opcional) y URL (esquema o `www.`), léxico ofensivo es-MX por palabra completa con allowlist de colisiones, corpus benigno versionado | `src/thehouse_genai/domain/moderation.py`, `tests/fixtures/moderation_benign_corpus.json` | `tests/test_moderation_policy.py` |
| B3 | Puerto, DTOs, errores, guard, fake y moderador local | `src/thehouse_genai/providers/moderation.py` | `tests/test_moderation_provider.py` |
| B4 | Integración en la salida: inyección del puerto, fail-closed, plantilla sin título (A6), allowlist de logs | `src/thehouse_genai/application/explain_match.py`, `api/app.py`, `api/routes/generative.py`, `infrastructure/logging.py`, `specs/003-smart-match-explanation/spec.md` | `tests/test_moderation_output.py` y ajustes de `tests/test_explain_match.py`, `tests/test_generative_api.py` |
| B5 | `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE` en `generateContent` | `src/thehouse_genai/providers/gemini.py` | `tests/test_gemini_safety.py` (MockTransport) |
| B6 | Cierre: checklist, evidencia, memoria, README y gates | `specs/006-moderation/checklist.md`, `evidence.md`, `memoria.md` | `ruff check .`, `mypy src`, `pytest`, `git diff --check` |

Cada bloque se implementa y prueba de forma independiente. No se toca `pyproject.toml`:
solo `re` y `unicodedata` de la stdlib.

## Decisiones que condicionan el plan

- A1: sin endpoint de contenido de usuarios en G06.
- A2: fail-closed en salida = fallback 200 `generated=false`.
- A3: `safetySettings` constante, umbral `BLOCK_MEDIUM_AND_ABOVE`, sin env nueva.
- A4: cero llamadas extra a Gemini.
- A5: se modera la salida por el puerto; la entrada sigue con 003/005.
- A6: la plantilla de fallback no incluye el título; se implementa en B4.
- A7: opción B futura con fail-closed `review` y LLM solo con flag opt-in.

## Contrato propuesto para la opción B (no implementado)

Deuda (f) de `memoria.md`; abrir como spec nueva si el requisito académico la exige.

`POST /api/v1/moderation/check`, con `X-Service-Key` y rate limit. Entrada camelCase y
`extra="forbid"`: `contentType` (`property_title`, `property_description`, `review`,
`report`), `text` (1–2 000 caracteres), `locale` (`es-MX`). Salida:
`{decision: "allow"|"review"|"block", reasons: [códigos estables], policyVersion}`.
Nunca se devuelve el texto ni el fragmento coincidente. Cero llamadas a Gemini en modo
local; el modo híbrido con LLM sería opt-in y costaría una llamada por contenido en
`review` sobre la misma clave (~15 RPM).

## Estrategia de pruebas

- Contenido permitido continúa el flujo sin cambios.
- Contenido bloqueado no se responde: degrada a fallback con motivo estable.
- Error/timeout del moderador aplica el fail-closed A2.
- Logs solo metadatos de la allowlist de `JsonFormatter`.
- Corpus benigno versionado con frases reales de rentas estudiantiles, incluidas
  `$2,800 MXN`, `1.3 km`, `91%`, `depósito de garantía`, `se aceptan mascotas` y
  `baño privado`, para detectar falsos positivos.
- Suite 100% sin red: el guard `block_network` sigue activo y el moderador es local.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Regresión de los 536 tests de 003/005 | Inyección del puerto solo desde la capa HTTP; en el caso de uso el moderador es opcional. Tests aditivos. |
| Falsos positivos con precios, distancias o porcentajes | Regex con límites de palabra, allowlist de colisiones y corpus benigno. |
| Más fallbacks por `safetySettings` | Umbral medio y monitoreo de `fallback_reason`. |
| Fuga de contenido en logs | Auditoría solo con metadatos; allowlist extendida. |
| Categorías ambiguas | Política versionada y códigos de motivo estables. |
| Moderador no disponible | Fail-closed A2 y motivo `MODERATION_UNAVAILABLE`. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde, sin red.
- Evidencia registrada, sin secretos y con revisión de seguridad.
- Solo entonces se cambia el estado a `IMPLEMENTED`.
