# Checklist — 005-security Seguridad de servicio e IA

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Threat model y data flow documentados.
- [ ] Endpoint generativo sin credencial devuelve 401 con sobre estándar.
- [ ] Tokens de usuario rechazados/no reenviados.
- [ ] Pruebas de PII y redacción de logs pasan.
- [ ] Corpus de prompt injection no altera contratos.
- [ ] Rate limit probado.
- [ ] Escaneo de secretos y dependencias en CI.

## Seguridad

- [ ] Secretos solo en entorno/gestor; nunca en repo, imagen ni logs.
- [ ] Autenticación de servicio con secreto rotable o mTLS acordado con Backend.
- [ ] Defensa en profundidad: validación de entrada, prompt delimitado, validación de salida.
- [ ] Minimización estricta de PII; rechazar dirección exacta y datos del propietario.
- [ ] Fail closed: si falla la autenticación o validación, no se llama al proveedor.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
