# Evidencia — 005-security Seguridad de servicio e IA

- **Estado:** PLANNED
- **Fecha:** —
- **Implementación:** no iniciada

## Resultado

Spec planificada. No existe implementación, ejecución de pruebas ni evidencia que
reportar. No se debe marcar como completada hasta cumplir sus criterios.

## Evidencia requerida al cerrar

- [ ] Threat model y data flow documentados.
- [ ] Endpoint generativo sin credencial devuelve 401 con sobre estándar.
- [ ] Tokens de usuario rechazados/no reenviados.
- [ ] Pruebas de PII y redacción de logs pasan.
- [ ] Corpus de prompt injection no altera contratos.
- [ ] Rate limit probado.
- [ ] Escaneo de secretos y dependencias en CI.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
