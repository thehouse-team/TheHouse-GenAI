# Checklist — 001 Foundation

## Funcional

- [x] `/health/live` devuelve 200 y payload estable.
- [x] `/health/ready` devuelve 200.
- [x] No existe ningún endpoint generativo.
- [x] No existe proveedor LLM ni llamada externa.
- [x] No hay cálculo de Smart Match ni acceso a propiedades.

## Configuración

- [x] `.env.example` incluye variables runtime y futuras.
- [x] `.env` está ignorado por git.
- [x] Timeout, tamaños y CORS tienen validación.
- [x] Configuración inválida falla claramente.
- [x] API key no se expone en `repr` ni en logs.

## Seguridad

- [x] Sin secretos reales en el repositorio.
- [x] Sin JWT, tokens ni API keys en logs.
- [x] Sin stack traces al cliente.
- [x] Request size limitado antes de la aplicación.
- [x] CORS restrictivo y configurable.
- [x] Request ID saneado y eco controlado.
- [x] Mensajes de error genéricos y sobre uniforme.

## Calidad

- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` estricto sin errores.
- [x] `pytest` con 21 tests aprobados.
- [x] CI con checkout, setup 3.12, install, ruff, mypy y pytest.
- [x] Todos los pasos del CI son bloqueantes.

## SDD y Git

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md`, `evidence.md` presentes.
- [x] Solo 001 está marcada como IMPLEMENTED.
- [x] `git diff --check` limpio.
- [x] Commit `chore: bootstrap generative ai service`.
- [x] Sin despliegue ni CD.
