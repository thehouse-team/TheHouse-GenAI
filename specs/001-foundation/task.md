# Tareas — 001 Foundation

## Estructura y configuración

- [x] Crear `pyproject.toml` con dependencias y herramientas.
- [x] Crear paquete `src/thehouse_genai` y capas base.
- [x] Implementar `Settings` con validación y `SecretStr`.
- [x] Implementar logging JSON estructurado.
- [x] Crear `.env.example` y `.gitignore`.

## API

- [x] Crear application factory e inyección de settings.
- [x] Implementar `GET /health/live`.
- [x] Implementar `GET /health/ready`.
- [x] Implementar sobre de error y handlers seguros.
- [x] Implementar middleware de request ID y logging de acceso.
- [x] Implementar límite de tamaño de request.
- [x] Configurar CORS restrictivo y exposición de docs por entorno.

## Pruebas

- [x] Probar `/health/live` 200.
- [x] Probar `/health/ready` 200.
- [x] Probar configuración válida.
- [x] Probar configuración inválida.
- [x] Probar errores consistentes (404, 413, 422, 500).
- [x] Probar que no se filtran detalles internos.
- [x] Probar CORS desactivado por defecto.

## CI y cierre

- [x] Crear `.github/workflows/ci.yml` bloqueante.
- [x] Ejecutar `ruff check .` en verde.
- [x] Ejecutar `mypy src` en verde.
- [x] Ejecutar `pytest` en verde.
- [x] Actualizar checklist y evidence.
- [x] Crear commit de bootstrap.
- [x] Verificar `git status` y `git diff --check`.
