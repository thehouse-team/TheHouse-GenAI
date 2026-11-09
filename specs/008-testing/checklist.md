# Checklist — 008-testing Estrategia de pruebas

- **Estado:** PLANNED

## Criterios de aceptación

- [ ] Estrategia y fixtures documentadas.
- [ ] Contract tests de explain-match y parse-search.
- [ ] Suite sin red y reproducible.
- [ ] Cobertura mínima alcanzada.
- [ ] Pruebas de seguridad integradas.
- [ ] CI ejecuta todo de forma bloqueante.

## Seguridad

- [ ] Fixtures sin PII ni secretos reales.
- [ ] Pruebas negativas de auth, PII y límites.
- [ ] No usar credenciales reales en tests.
- [ ] Registrar fallos sin volcar prompts sensibles.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
