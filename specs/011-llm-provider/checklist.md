# Checklist — 011-llm-provider Proveedor LLM real

- **Estado:** IMPLEMENTED
- **Fecha de activación:** 2026-11-15
- **Fecha de cierre:** 2026-11-16

## Evaluación y decisión

- [x] Matriz con precio, capa gratuita, latencia, JSON estructurado, español y Python.
      La latencia y la calidad en español se midieron el 2026-11-16 con el smoke test
      manual; OpenAI y Azure quedan «no medido» por falta de acceso.
- [x] Fuentes citadas por dato.
- [x] Documento de decisión con proveedor elegido, alternativa y motivo.
- [x] Condiciones de revisión del documento de decisión.

## Criterios de aceptación

- [x] Adaptador implementando `GenerativeAiProvider` sin cambios en application/domain.
      `src/thehouse_genai/providers/gemini.py`; `application/` y `domain/` no se
      modificaron y el test de fronteras impide que dependan de una implementación.
- [x] Respuesta del vendor validada y normalizada al DTO interno.
- [x] Errores 401/429/5xx mapeados a la taxonomía propia.
- [x] Timeout y límite de entrada verificados.
- [x] Proveedor registrado en la factory y validado en `Settings`.
- [x] Tests del adaptador en verde y sin red.
- [x] El modelo y su versión aparecen en logs internos y en ninguna respuesta de la API.
      `provider_model` solo llega al log interno; `git grep provider_model -- src/thehouse_genai/api/`
      no devuelve nada.
- [x] Script de smoke test manual opt-in y fuera de CI.
- [x] `ruff check .`, `mypy src` y `pytest` en verde sin acceso a red.

## Seguridad

- [x] La credencial es `SecretStr` y no aparece en logs, `repr` ni respuestas.
- [x] No registrar prompts ni respuestas completas; solo metadatos.
- [x] Redactar `Authorization` y claves del vendor. La clave viaja solo en la cabecera
      `x-goog-api-key` y ni la URL ni el log ni las excepciones la contienen, así que
      no hay nada que redaccionar.
- [x] Sin secretos versionados ni `.env` en el repositorio. `git check-ignore -v .env`
      lo confirma y una búsqueda del prefijo de la clave del vendor en todo el
      repositorio no devuelve nada.
- [x] El smoke test exige confirmación explícita y no imprime la clave.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `mypy --strict scripts/smoke_provider.py` sin errores.
- [x] `pytest` en verde y sin red (279 tests con el guard de red activo).
- [x] `memoria.md` actualizado con la decisión de proveedor.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.
