# Checklist — 011-llm-provider Proveedor LLM real

- **Estado:** PLANNED

## Evaluación y decisión

- [ ] Matriz con precio, capa gratuita, latencia, JSON estructurado, español y Python.
- [ ] Fuentes citadas por dato.
- [ ] Documento de decisión con proveedor elegido, alternativa y motivo.
- [ ] Condiciones de revisión del documento de decisión.

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

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] `memoria.md` actualizado con la decisión de proveedor.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
