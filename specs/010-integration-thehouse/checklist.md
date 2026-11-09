# Checklist — 010-integration-thehouse Integración con TheHouse Backend

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Contrato aprobado y contract tests en ambos repos.
- [ ] Auth de servicio validada en staging.
- [ ] Timeouts, reintentos y circuit breaker probados.
- [ ] Fallback seguro verificado.
- [ ] E2E staging con datos sintéticos.
- [ ] Runbook y rollback documentados.

## Seguridad

- [ ] Sin secretos en Android; el cliente nunca conoce la credencial de servicio.
- [ ] Filtro de PII antes de la llamada.
- [ ] Sin logs de prompts/respuestas completos.
- [ ] Rate limit y cuotas alineados con Backend.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
