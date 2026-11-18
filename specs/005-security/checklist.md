# Checklist — 005-security Seguridad de servicio e IA

- **Estado:** IMPLEMENTED
- **Plan aprobado:** 2026-11-17
- **Cierre:** 2026-11-17

## Criterios de aceptación

- [x] B0: threat model y data flow documentados (apéndice de `spec.md`).
- [x] Endpoint generativo sin credencial devuelve 401 con sobre estándar (re-verificado).
- [x] Rotación: actual y anterior aceptadas; solo anterior → 401; `|=` sobre todas;
      `SERVICE_KEY_PREVIOUS` genérica ignorada.
- [x] Tokens de usuario rechazados/no reenviados.
- [x] Allowlist de campos del prompt con test que falla si se agrega uno nuevo.
- [x] Corpus versionado de prompt injection sin red; salida normalizada contra homoglifos.
- [x] Rate limit 429 con sobre estándar y `Retry-After`; límite por proceso documentado.
- [x] Headers de seguridad en todas las respuestas; OpenAPI apagada fuera de
      `local`/`test` (re-verificado).
- [x] Logs de 401/429 con `request_id` y `reason`, sin clave ni body; fingerprint en 429.
- [x] Secret scanning, push protection, Dependabot y CodeQL documentados; `pip-audit` en
      CI con `continue-on-error`.

## Seguridad

- [x] Secretos solo en entorno/gestor; nunca en repo, imagen ni logs.
- [x] Autenticación de servicio con secreto rotable; mTLS fuera de alcance (D2).
- [x] Defensa en profundidad: validación de entrada, prompt delimitado, validación de
      salida y normalización de homoglifos.
- [x] Minimización estricta de PII: allowlist de los 12 campos del prompt.
- [x] Fail closed: si falla la autenticación o validación no se llama al proveedor;
      tampoco si solo existe la clave anterior (D10).

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `pytest` en verde y sin red (536 tests, 1 warning heredado de 008).
- [x] Sin secretos, PII ni tokens en código, logs o fixtures.
- [x] Sin endpoints ni proveedores reales fuera de alcance.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.

## Comportamiento conocido (deuda)

- [x] Un body que no es JSON válido se rechaza al parsearse, antes de la autenticación
      (422 en TestClient, 400 en la prueba manual real). Mensaje genérico, sin datos de la
      request. Documentado en `spec.md` y `evidence.md`; deuda registrada en `memoria.md`.
      No se cambió el orden de procesamiento.
