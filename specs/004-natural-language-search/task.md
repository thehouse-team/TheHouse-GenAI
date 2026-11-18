# Tareas — 004-natural-language-search Búsqueda en lenguaje natural

- **Estado:** ACTIVE

## B0 — Activación y contrato (docs)

- [x] Activar 004 en `memoria.md` y en los 5 archivos del SDD.
- [x] Reescribir spec/plan/task/checklist con el contrato final (`maxDistanceKm`,
      `promptVersion`), decisiones D1–D13 y 4 ajustes obligatorios.
- [x] Actualizar dependencias (001, 002, 003, 005, 006, 007, 011), quitar el 502 y
      alinear `AGENTS.md` y `README.md`.
- [x] Gates en verde y commit documental.

## B1 — Dominio

- [ ] Contratos `ParseSearchRequest`, `SearchFilters`, `ParseSearchResponse` y
      `ParseSearchCompletion` con aliases, límites y `extra="forbid"`.
- [ ] Extractores deterministas de dinero, distancia, universidad, servicios y mascotas.
- [ ] `redact_pii` reutilizando los detectores de `domain/moderation.py`.
- [ ] Guard de texto compartido en `domain/text_guard.py` con re-exports que mantienen
      verdes los tests de 003 sin cambios.
- [ ] Tests en `test_domain_search_filters.py` y `test_search_text_guard.py`.

## B2 — Guardrails

- [ ] Validador anti-alucinación por evidencia (poda de filtros no respaldados).
- [ ] Cálculo determinista de `confidence` con reglas de rango y otra moneda.

## B3 — Caso de uso

- [ ] Prompt `parse_search_v1` con salida JSON de solo `filters`.
- [ ] Proveedor, fallback 200, presupuesto y métricas reutilizados.

## B4 — Moderación y PII

- [ ] Moderación de entrada fail-closed y de salida por el puerto de 006.
- [ ] Redacción end-to-end antes del prompt.

## B5 — HTTP y observabilidad

- [ ] Endpoint autenticado con rate limit y errores seguros.
- [ ] Ruta cerrada `parse-search`, nuevos contadores/razones y correlación de logs.

## B6 — Corpus y script manual

- [ ] Corpus versionado de 28 frases + 2 casos de contrato.
- [ ] `scripts/smoke_parse_search.py` opt-in, nunca en CI.

## B7 — Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest` sin red.
- [ ] Revisar seguridad, secretos, PII y ausencia de caracteres CJK.
- [ ] Cambiar el estado a `IMPLEMENTED` solo al cumplir todo.
