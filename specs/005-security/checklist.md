# Checklist — 005-security Seguridad de servicio e IA

- **Estado:** ACTIVE
- **Plan aprobado:** 2026-11-17

## Criterios de aceptación

- [x] B0: threat model y data flow documentados (apéndice de `spec.md`).
- [ ] Endpoint generativo sin credencial devuelve 401 con sobre estándar (re-verificado).
- [ ] Rotación: actual y anterior aceptadas; solo anterior → 401; `|=` sobre todas;
      `SERVICE_KEY_PREVIOUS` genérica ignorada.
- [ ] Tokens de usuario rechazados/no reenviados.
- [ ] Allowlist de campos del prompt con test que falla si se agrega uno nuevo.
- [ ] Corpus versionado de prompt injection sin red; salida normalizada contra homoglifos.
- [ ] Rate limit 429 con sobre estándar y `Retry-After`; límite por proceso documentado.
- [ ] Headers de seguridad en todas las respuestas; OpenAPI apagada fuera de
      `local`/`test` (re-verificado).
- [ ] Logs de 401/429 con `request_id` y `reason`, sin clave ni body; fingerprint en 429.
- [ ] Secret scanning, push protection y Dependabot documentados; `pip-audit` en CI con
      `continue-on-error`.

## Seguridad

- [x] B0: secretos solo en entorno/gestor; nunca en repo, imagen ni logs.
- [ ] Autenticación de servicio con secreto rotable; mTLS fuera de alcance (D2).
- [ ] Defensa en profundidad: validación de entrada, prompt delimitado, validación de
      salida y normalización de homoglifos.
- [ ] Minimización estricta de PII: allowlist de los 12 campos del prompt.
- [ ] Fail closed: si falla la autenticación o validación no se llama al proveedor;
      tampoco si solo existe la clave anterior (D10).

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
