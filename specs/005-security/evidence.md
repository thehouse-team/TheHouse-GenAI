# Evidencia — 005-security Seguridad de servicio e IA

- **Estado:** ACTIVE
- **Fecha:** 2026-11-17
- **Implementación:** en curso (B0 completado; B1 en ejecución)

## Resultado

Spec activada el 2026-11-17 con plan aprobado sobre `feature/security-hardening`.
Quedan registradas las decisiones D1–D12, la corrección de dependencias (ya no depende
de 004) y el alcance de mTLS, presupuesto global, CI y runbook. Aún no hay implementación
ni resultados de gates que reportar en esta spec: se registrarán bloque a bloque y no se
marcará como completada hasta cumplir todos sus criterios.

## Evidencia requerida al cerrar

- [ ] Threat model y data flow documentados (apéndice).
- [ ] 401 con sobre estándar (re-verificación de 003).
- [ ] Rotación de clave, fail closed y `SERVICE_KEY_PREVIOUS` ignorada.
- [ ] Tokens de usuario rechazados/no reenviados; allowlist del schema exacta.
- [ ] Logs de 401/429 con `request_id`, `reason` y fingerprint; sin clave ni body.
- [ ] Corpus de inyección versionado y sin red; salida normalizada.
- [ ] 429 con sobre estándar y `Retry-After`; límite por proceso documentado.
- [ ] Headers de seguridad y OpenAPI apagada fuera de `local`/`test`.
- [ ] Secret scanning, push protection, Dependabot y `pip-audit` documentados/ejecutados.
- [ ] Resultados de `ruff check .`, `mypy src`, `pytest` y `git diff --check`.
- [ ] Revisión de seguridad y ausencia de secretos, PII y CJK.
- [ ] Referencia al commit que implementa la spec.
