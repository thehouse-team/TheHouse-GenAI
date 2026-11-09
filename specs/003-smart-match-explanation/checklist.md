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

## Seguridad

- [ ] Minimizar PII: sin nombre de propietario, dirección exacta ni tokens.
- [ ] No registrar prompt ni explicación completos por defecto.
- [ ] Defensa contra prompt injection en todos los campos de texto libre.
- [ ] Limitar longitud de entrada y salida.
- [ ] Autenticación servicio-a-servicio antes de exponer el endpoint (spec 005).

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
