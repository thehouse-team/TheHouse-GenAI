# Evidencia — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED
- **Fecha:** —
- **Implementación:** no iniciada

## Resultado

Spec planificada. No existe implementación, ejecución de pruebas ni evidencia que
reportar. No se debe marcar como completada hasta cumplir sus criterios.

## Evidencia requerida al cerrar

- [ ] Interfaz y DTOs aprobados, tipados en modo estricto.
- [ ] Test de frontera: application/domain no importan httpx ni SDKs de proveedor.
- [ ] Timeout verificado con transporte simulado.
- [ ] Errores 401/429/5xx del proveedor mapeados sin filtrar detalles internos.
- [ ] Fake provider cubre éxito, error y timeout.
- [ ] Configuración incompleta o inválida falla al iniciar.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
