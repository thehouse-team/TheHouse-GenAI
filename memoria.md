# Memoria del proyecto — TheHouse GenAI

Última actualización: 2026-11-08

## Identidad

Repositorio independiente para IA generativa de TheHouse. Recibe contexto calculado por
TheHouse Backend y produce explicaciones o filtros. No sustituye al Backend, no calcula
Smart Match, no consulta propiedades y no contiene Mobile.

## Estado de specs

| Spec | Estado | Alcance |
| --- | --- | --- |
| 001-foundation | IMPLEMENTED | Servicio mínimo, health, config, seguridad base, tests, CI |
| 002-provider-abstraction | PLANNED | Interfaz LLM, DTOs, adaptador httpx, fake de test |
| 003-smart-match-explanation | PLANNED | Explicación de match sin alterar hechos |
| 004-natural-language-search | PLANNED | Parseo de búsqueda a filtros, nunca propiedades |
| 005-security | PLANNED | Autenticación servicio-a-servicio, PII, prompt injection |
| 006-moderation | PLANNED | Política y moderación de contenido |
| 007-observability | PLANNED | Métricas, trazas, SLOs y alertas |
| 008-testing | PLANNED | Estrategia completa y contract tests |
| 009-ci-cd | PLANNED | Pipeline completo y despliegue futuro |
| 010-integration-thehouse | PLANNED | Contratos y operación con Backend |

## Decisiones tomadas en 001

- Python 3.12 + FastAPI + Pydantic v2 + pydantic-settings; sin Docker.
- Paquete `thehouse_genai` bajo `src/`, instalable con `pip install -e ".[dev]"`.
- Configuración tipada y validada al arrancar. Valores inválidos fallan con error claro.
- `GENAI_API_KEY` se modela como `SecretStr`; no se usa en G01.
- CORS vacío por defecto; se rechazan comodines y orígenes no HTTP(S).
- Límite de request (`MAX_REQUEST_BYTES`) aplicado antes de la lógica de aplicación.
- ID de correlación saneado, eco en `X-Request-ID` y logging JSON sin secretos.
- Sobre de error único: `{"error": {"code", "message", "request_id"}}`.
- Health: `GET /health/live` y `GET /health/ready`, ambos 200 con payload estable.
- Documentación OpenAPI solo en `local` y `test`.
- CI bloqueante con ruff, mypy y pytest; sin CD ni despliegue.

## Contrato de health

```json
{"status": "ok", "service": "thehouse-genai", "version": "0.1.0"}
```

## Configuración futura reservada

`GENAI_PROVIDER`, `GENAI_API_KEY`, `GENAI_MODEL`, `GENAI_TIMEOUT_SECONDS` (15) y
`GENAI_MAX_INPUT_CHARS` (4000). Aunque existen en `Settings`, ningún código los usa para
llamadas externas en G01.

## Evidencia resumida

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict).
- `pytest`: 21 tests aprobados.
- Commit de bootstrap: `chore: bootstrap generative ai service`.

## Deuda y pendientes

- Definir interfaz de proveedor y fake (002).
- Contratos y guardrails de explicación (003) y parseo (004).
- Autenticación servicio-a-servicio y minimización de PII (005).
- Moderación, observabilidad avanzada, contract tests e integración (006–010).
- No hay despliegue ni credenciales reales configuradas.

## Próximo paso

Cerrar G01 y planificar `002-provider-abstraction` sin activar ningún proveedor real.
