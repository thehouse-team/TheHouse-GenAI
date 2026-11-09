# 001 — Foundation

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-08
- **Depende de:** —
- **Habilita:** 002–010

## Objetivo

Crear el servicio mínimo ejecutable de TheHouse GenAI con health probes, configuración
tipada, contrato de errores, controles de seguridad base, pruebas y CI bloqueante, sin
proveedor LLM ni endpoints generativos.

## Contexto

TheHouse Backend ya cubre auth, perfiles, propiedades, favoritos, visitas, arrendadores y
moderación. Este repositorio solo alojará IA generativa y debe nacer aislado, seguro y
verificable. El requisito académico exige una función ML (externa, Smart Match) y una
función de IA generativa (aquí, futura). La separación es obligatoria.

## Alcance

### Incluido

- Paquete Python instalable `thehouse_genai` bajo `src/`.
- Capas `api/`, `application/`, `domain/`, `providers/`, `infrastructure/`.
- `GET /health/live` y `GET /health/ready`, ambos 200.
- Configuración por entorno + `.env` opcional, con validación estricta.
- Sobre de error uniforme y manejo seguro de excepciones.
- Middleware de request ID, logging JSON y límite de tamaño.
- CORS configurable, vacío por defecto y sin comodines.
- `.env.example`, `.gitignore`, CI y documentación SDD.
- Tests de health, configuración, errores y límites.

### Excluido

- `POST /api/v1/generative/explain-match` y `POST /api/v1/generative/parse-search`.
- Proveedor LLM real, llamadas externas, prompts de negocio.
- Smart Match, consulta de propiedades, base de datos y autenticación de usuarios.
- Mobile, Backend, Docker, despliegue y CD.

## Requisitos funcionales

- **RF-01:** `GET /health/live` responde 200 con payload estable.
- **RF-02:** `GET /health/ready` responde 200 cuando la configuración cargó.
- **RF-03:** la configuración inválida impide el arranque con un error claro.
- **RF-04:** toda respuesta de error usa `{"error": {"code", "message", "request_id"}}`.
- **RF-05:** cada request recibe un ID saneado, se devuelve en `X-Request-ID` y se registra.
- **RF-06:** requests que exceden `MAX_REQUEST_BYTES` reciben 413 sin llegar a la app.
- **RF-07:** los logs son JSON y no incluyen headers, cuerpos, tokens ni API keys.
- **RF-08:** los errores no controlados devuelven 500 genérico sin stack trace.

## Requisitos no funcionales

- Python 3.12+, FastAPI, Pydantic v2, Uvicorn, httpx, pytest, ruff y mypy.
- `mypy` en modo estricto sobre `src`.
- CORS restrictivo: orígenes explícitos, sin `*`, sin credenciales por defecto.
- OpenAPI expuesto solo en `local` y `test`.
- Sin secretos en el repositorio.

## Contrato de health

```json
{"status": "ok", "service": "thehouse-genai", "version": "0.1.0"}
```

## Criterios de aceptación

- [x] `/health/live` y `/health/ready` responden 200.
- [x] Configuración válida carga desde entorno y valores por defecto.
- [x] Timeout, límites y CORS inválidos fallan con `ValidationError`.
- [x] API key se representa con `SecretStr` y no aparece en `repr`.
- [x] 404, 413, 422 y 500 usan el sobre de error y no filtran internos.
- [x] Límite de request aplicado y probado.
- [x] Logging JSON con request ID y sin datos sensibles.
- [x] `ruff check .`, `mypy src` y `pytest` en verde.
- [x] CI con checkout, setup, install, ruff, mypy y pytest.
- [x] SDD completo y solo esta spec marcada como implementada.

## Riesgos residuales

- La autenticación servicio-a-servicio, moderación y observabilidad avanzada quedan para
  005, 006 y 007; G01 no expone endpoints generativos, por lo que no hay superficie LLM.
- No se ha ejecutado el workflow en GitHub todavía; la evidencia local replica sus pasos.
