# Evidencia — 001 Foundation

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-08
- **Commit:** `chore: bootstrap generative ai service`
- **Entorno:** Windows, Python 3.12.10, venv local

## Comandos y resultados

| Comando | Resultado |
| --- | --- |
| `ruff check .` | Sin hallazgos |
| `mypy src` | `Success: no issues found in 15 source files` |
| `pytest` | `21 passed` |
| `git diff --check` | Sin errores de whitespace |

## Cobertura funcional evidenciada

- Health live y ready: 200 y payload `{"status":"ok","service":"thehouse-genai","version":"0.1.0"}`.
- Configuración: defaults, entorno, CORS JSON/CSV, seis casos inválidos, wildcard y
  esquema no HTTP rechazados, secreto oculto en `repr`.
- Errores: 404 `NOT_FOUND`, 413 `PAYLOAD_TOO_LARGE`, 422 `VALIDATION_ERROR` y 500
  `INTERNAL_ERROR`; el 500 no contiene el mensaje interno ni `Traceback`.
- Request ID: se respeta uno válido y se reemplaza uno con salto de línea.
- CORS: ausente por defecto ante un origen no configurado.

## Archivos clave

- `src/thehouse_genai/api/app.py`
- `src/thehouse_genai/api/errors.py`
- `src/thehouse_genai/api/middleware.py`
- `src/thehouse_genai/infrastructure/config.py`
- `src/thehouse_genai/infrastructure/logging.py`
- `tests/` (4 archivos de prueba)
- `.github/workflows/ci.yml`

## Verificaciones de límites

- No se creó proveedor LLM ni adaptador real.
- No se crearon endpoints `explain-match` ni `parse-search`.
- No se consultó ningún repositorio externo.
- No se configuraron credenciales ni despliegues.

## Pendiente fuera de G01

Autenticación servicio-a-servicio (005), moderación (006), observabilidad avanzada
(007), contract tests (008), CD (009) e integración con Backend (010).
