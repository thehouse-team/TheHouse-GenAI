# Evidencia — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** PLANNED
- **Fecha:** —
- **Implementación:** no iniciada

## Resultado

Spec planificada. No existe implementación, ejecución de pruebas ni evidencia que
reportar. No se debe marcar como completada hasta cumplir sus criterios.

## Evidencia requerida al cerrar

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
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
