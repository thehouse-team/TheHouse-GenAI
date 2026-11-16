# Checklist — 011-llm-provider Proveedor LLM real

- **Estado:** ACTIVE
- **Fecha de activación:** 2026-11-15

## Evaluación y decisión

- [x] Matriz con precio, capa gratuita, latencia, JSON estructurado, español y Python.
      La latencia y la calidad en español quedan marcadas «pendiente de medir» hasta
      el bloque B8.
- [x] Fuentes citadas por dato.
- [x] Documento de decisión con proveedor elegido, alternativa y motivo.
- [x] Condiciones de revisión del documento de decisión.

## Criterios de aceptación

- [ ] Adaptador implementando `GenerativeAiProvider` sin cambios en application/domain.
- [ ] Respuesta del vendor validada y normalizada al DTO interno.
- [ ] Errores 401/429/5xx mapeados a la taxonomía propia.
- [ ] Timeout y límite de entrada verificados.
- [ ] Proveedor registrado en la factory y validado en `Settings`.
- [ ] Tests del adaptador en verde y sin red.
- [ ] El modelo y su versión aparecen en logs internos y en ninguna respuesta de la API.
- [ ] Script de smoke test manual opt-in y fuera de CI.

## Seguridad

- [ ] La credencial es `SecretStr` y no aparece en logs, `repr` ni respuestas.
- [ ] No registrar prompts ni respuestas completas; solo metadatos.
- [ ] Redactar `Authorization` y claves del vendor.
- [ ] Sin secretos versionados ni `.env` en el repositorio.
- [ ] El smoke test exige confirmación explícita y no imprime la clave.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [x] `memoria.md` actualizado con la decisión de proveedor.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
