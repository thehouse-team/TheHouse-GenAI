# Plan — 001 Foundation

- **Estado:** IMPLEMENTED
- **Enfoque:** monolito HTTP mínimo, capas preparadas y gates locales/CI.

## Decisiones técnicas

1. **Paquete `src/thehouse_genai`** instalable con setuptools; evita imports accidentales
   desde la raíz y permite `pip install -e ".[dev]"`.
2. **Application factory** `create_app(settings)` para inyectar configuración en tests sin
   depender de variables globales.
3. **pydantic-settings** con `.env` opcional; `SecretStr` para API keys; validadores para
   timeout, tamaños y CORS.
4. **Middleware ASGI propio** para request ID y límite de tamaño, evitando confiar en
   cabeceras del cliente y cubriendo cuerpos declarados o transmitidos.
5. **Errores centralizados** con mensajes seguros; los detalles internos solo van al log.
6. **Logging JSON** con campos allowlist y `X-Request-ID`; acceso de Uvicorn desactivado
   para no duplicar logs en texto plano.
7. **CORS** vacío por defecto; se rechazan comodines y esquemas no HTTP(S).
8. **Health sin dependencias externas**; readiness queda preparado para futuras comprobaciones.
9. **CI** replica exactamente los comandos locales y es bloqueante; sin CD.

## Pasos ejecutados

1. Crear estructura de paquete, capas y configuración de proyecto.
2. Implementar `Settings`, logging estructurado y factory FastAPI.
3. Añadir health probes, sobre de errores, request ID y límite de request.
4. Configurar CORS restrictivo y ocultar docs fuera de local/test.
5. Añadir tests de health, configuración, errores y límites.
6. Crear workflow de CI, `.env.example`, `.gitignore` y SDD.
7. Ejecutar ruff, mypy y pytest; corregir hallazgos.
8. Registrar evidencia y preparar commit de bootstrap.

## Estructura resultante

```text
src/thehouse_genai/
  api/app.py, errors.py, middleware.py, request_context.py
  api/routes/health.py
  application/__init__.py
  domain/__init__.py
  providers/__init__.py
  infrastructure/config.py, logging.py
tests/
  conftest.py, test_health.py, test_config.py, test_errors.py
```

## Estrategia de pruebas

- **API:** TestClient sobre app construida con settings de test.
- **Configuración:** defaults, lectura de entorno, CORS JSON/lista, casos inválidos,
  representación segura de secretos.
- **Errores:** 404, 413, 422 y 500; ausencia de detalles internos.
- **Seguridad:** CORS desactivado por defecto y request ID no confiable reemplazado.

## Puerta de salida

Los tres gates en verde, CI versionado, evidencia actualizada y commit con mensaje
`chore: bootstrap generative ai service`. Sin despliegue.
