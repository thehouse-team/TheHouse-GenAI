# Checklist — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Interfaz y DTOs aprobados, tipados en modo estricto.
- [ ] Test de frontera: application/domain no importan httpx ni SDKs de proveedor.
- [ ] Timeout verificado con transporte simulado.
- [ ] Errores 401/429/5xx del proveedor mapeados sin filtrar detalles internos.
- [ ] Fake provider cubre éxito, error y timeout.
- [ ] Configuración incompleta o inválida falla al iniciar.

## Seguridad

- [ ] No registrar prompts ni respuestas completas por defecto; solo metadatos.
- [ ] Redactar `Authorization` y cualquier clave en logs y excepciones.
- [ ] Validar tamaño y campos permitidos antes de enviar al proveedor.
- [ ] Sin reintentos en esta spec para no amplificar coste ni latencia.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
