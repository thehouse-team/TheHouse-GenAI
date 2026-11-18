# Evidencia — 007-observability Observabilidad

- **Estado:** ACTIVE
- **Fecha:** 2026-11-18
- **Implementación:** en curso (B0 completado; B1 en curso)

## B0 — Activación documental

Gates del bloque documental (resultados reales):

| Gate | Comando | Salida |
| --- | --- | --- |
| Lint | `.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` |
| Tipado | `.venv\Scripts\python.exe -m mypy src` | `Success: no issues found in 27 source files` |
| Tests | `.venv\Scripts\python.exe -m pytest` | `688 passed, 1 warning in 3.11s` |

El único warning es el `StarletteDeprecationWarning` heredado de `TestClient` con `httpx`
(deuda (e)/006-(d), registrada para 008). Sin red: guard `block_network` activo.

Commit: `docs: activate spec 007 observability`.

## Resultado

Spec activada con plan aprobado y decisiones 1–9. Sin implementación de código en B0; la
evidencia de B1 y posteriores se añadirá con resultados reales antes del cierre.

## Evidencia requerida al cerrar

- [ ] Schema de logs documentado y probado.
- [ ] Métricas expuestas internamente con nombres estables.
- [ ] Trazas correlacionan una request completa (por `request_id`).
- [ ] SLOs y alertas aprobados.
- [ ] Pruebas garantizan ausencia de contenido sensible.
- [ ] Coste/tokens medidos sin almacenar texto.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
