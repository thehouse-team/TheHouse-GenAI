# Checklist — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** ACTIVE

## Contrato y criterios de aceptación

- [ ] Respuesta exacta `{filters, confidence, generated, promptVersion}` (D1).
- [ ] `filters` con exactamente `maxBudget`, `currency`, `university`,
      `essentialServices`, `petsAllowed` y `maxDistanceKm`; `extra="forbid"`.
- [ ] `maxDistanceKm` distingue `3 km` de `3k`; minutos y cuadras no se convierten.
- [ ] `university` respaldado por texto normalizado o alias canónico (UTTT).
- [ ] "entre 2000 y 3000" → `maxBudget=3000`; confianza máxima `medium`.
- [ ] Cada filtro no respaldado se poda sin rechazar la respuesta.
- [ ] `confidence` determinista; el modelo solo devuelve `filters`.
- [ ] Fallos del proveedor, timeout, JSON inválido y presupuesto → 200 vacío + `low`,
      nunca 502.
- [ ] Query válida pero vaga, o solo-PII, → 200 vacío + `low`.
- [ ] Correos, teléfonos y URLs redactados antes del prompt.
- [ ] Inyección escapada y registrada, nunca rechazada.
- [ ] Query ofensiva → 200 vacío + `low` sin llamada al proveedor.
- [ ] Salida moderada con fail-closed.
- [ ] 401 sin credencial; 422 en query vacía/oversized; 429 con `Retry-After`.
- [ ] Corpus de 28 frases + 2 casos de contrato, 100% sin red.

## Seguridad y privacidad

- [ ] Límite de 500 caracteres y longitud de campos de salida acotada.
- [ ] Query completa nunca registrada; sin bodies ni credenciales en logs.
- [ ] Datos no confiables delimitados y escapados con el guard compartido.
- [ ] Autenticación servicio-a-servicio y rotación de 005 reutilizadas.
- [ ] Sin secretos, PII ni tokens en código, logs, métricas ni fixtures.
- [ ] Sin caracteres CJK ni de ancho completo.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] Decisiones D1–D13 y 4 ajustes registrados en `memoria.md`.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] `git diff --check` limpio.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
