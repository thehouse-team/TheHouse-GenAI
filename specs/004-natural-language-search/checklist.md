# Checklist — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** IMPLEMENTED

## Contrato y criterios de aceptación

- [x] Respuesta exacta `{filters, confidence, generated, promptVersion}` (D1).
- [x] `filters` con exactamente `maxBudget`, `currency`, `university`,
      `essentialServices`, `petsAllowed` y `maxDistanceKm`; `extra="forbid"`.
- [x] `maxBudget` y `maxDistanceKm` son números JSON (int/float) o `null`, nunca strings.
- [x] `maxDistanceKm` distingue `3 km` de `3k`; minutos y cuadras no se convierten.
- [x] `university` respaldado por texto normalizado o alias canónico (UTTT, UNAM).
- [x] "entre 2000 y 3000" → `maxBudget=3000`; confianza máxima `medium`.
- [x] Cada filtro no respaldado se poda sin rechazar la respuesta; servicios se
      normalizan, se deduplican y los desconocidos se podan con `PrunedField`.
- [x] `confidence` determinista; el modelo solo devuelve `filters`.
- [x] Fallos del proveedor, timeout, JSON inválido y presupuesto → 200 vacío + `low`,
      nunca 502.
- [x] Query válida pero vaga, o solo-PII, → 200 vacío + `low`.
- [x] Correos, teléfonos y URLs redactados antes del prompt.
- [x] Inyección escapada y registrada, nunca rechazada.
- [x] Query ofensiva → 200 vacío + `low` sin llamada al proveedor.
- [x] Salida moderada con fail-closed.
- [x] 401 sin credencial (incluida la clave de métricas); 422 en query vacía, en blanco,
      oversized, con locale extraño o campos extra; 429 con `Retry-After`.
- [x] Corpus de 28 casos + 2 de contrato (30 en total), 100% sin red.
- [x] `X-Request-ID` y headers de seguridad en respuestas; ruta `parse-search` en métricas.

## Seguridad y privacidad

- [x] Límite de 500 caracteres y longitud de campos de salida acotada.
- [x] Query completa nunca registrada; sin bodies ni credenciales en logs.
- [x] Datos no confiables delimitados y escapados con el guard compartido.
- [x] Autenticación servicio-a-servicio y rotación de 005 reutilizadas.
- [x] Sin secretos, PII ni tokens en código, logs, métricas ni fixtures.
- [x] Sin caracteres CJK ni de ancho completo.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] Decisiones D1–D13 y 4 ajustes registrados en `memoria.md`.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `mypy --strict scripts/smoke_parse_search.py` sin errores.
- [x] `pytest` en verde y sin red.
- [x] `git diff --check` limpio.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.
