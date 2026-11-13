# Checklist — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Contrato request/response documentado y validado.
- [ ] Explicación de fixture cita solo hechos permitidos.
- [ ] Se rechazan números y servicios ausentes en la entrada.
- [ ] Prompt injection en título/descripción no cambia reglas ni hechos.
- [ ] Score faltante o fuera de rango devuelve 422.
- [ ] Pruebas con fake provider, sin red.
- [ ] No existe acceso a base de datos ni a propiedades.
- [ ] Endpoint sin `X-Service-Key` devuelve 401 con el sobre estándar.
- [ ] `X-Service-Key` incorrecto devuelve 401 sin revelar si la credencial existe.
- [ ] La credencial no aparece en logs ni en el `repr` de `Settings`.

## Seguridad

- [ ] Minimizar PII: sin nombre de propietario, dirección exacta ni tokens.
- [ ] No registrar prompt ni explicación completos por defecto.
- [ ] Defensa contra prompt injection en todos los campos de texto libre.
- [ ] Limitar longitud de entrada y salida.
- [ ] Autenticación mínima de servicio implementada (`X-Service-Key`, `SecretStr`,
      comparación en tiempo constante, 401 con el sobre estándar).
- [ ] La autenticación endurecida (rotación, mTLS, rate limiting) queda para la spec 005.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
