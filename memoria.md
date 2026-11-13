# Memoria del proyecto — TheHouse GenAI

Última actualización: 2026-11-12

## Identidad

Repositorio independiente para IA generativa de TheHouse. Recibe contexto calculado por
TheHouse Backend y produce explicaciones o filtros. No sustituye al Backend, no calcula
Smart Match, no consulta propiedades y no contiene Mobile.

## Estado de specs

| Spec | Estado | Alcance |
| --- | --- | --- |
| 001-foundation | IMPLEMENTED | Servicio mínimo, health, config, seguridad base, tests, CI |
| 002-provider-abstraction | PLANNED | Puerto `GenerativeAiProvider`, DTOs, errores, fake y factory (offline) |
| 003-smart-match-explanation | PLANNED | Explicación de match sin alterar hechos, con auth mínima de servicio |
| 004-natural-language-search | PLANNED | Parseo de búsqueda a filtros, nunca propiedades |
| 005-security | PLANNED | Autenticación de servicio endurecida, PII, prompt injection |
| 006-moderation | PLANNED | Política y moderación de contenido |
| 007-observability | PLANNED | Métricas, trazas, SLOs y alertas |
| 008-testing | PLANNED | Estrategia completa y contract tests (transversal, cierra en G09) |
| 009-ci-cd | PLANNED | Pipeline completo y despliegue futuro |
| 010-integration-thehouse | PLANNED | Contratos y operación con Backend |
| 011-llm-provider | PLANNED | Evaluación de proveedores y adaptador real detrás del puerto |

## Mapeo de fases

| Fase | Spec | Contenido |
| --- | --- | --- |
| G01 | 001-foundation | Servicio base, health, configuración, CI (IMPLEMENTED) |
| G02 | 002-provider-abstraction | Puerto LLM, DTOs, errores, fake y factory, 100% offline |
| G03 | 011-llm-provider | Evaluación de proveedores y adaptador real |
| G04 | 003-smart-match-explanation | Endpoint explain-match con auth mínima de servicio |
| G05 | 005-security | Endurecimiento de seguridad, PII, prompt injection |
| G06 | 006-moderation | Moderación de contenido |
| G07 | 007-observability | Observabilidad, métricas y SLOs |
| G08 | 004-natural-language-search | Endpoint parse-search con auth endurecida |
| G09 | 010-integration-thehouse | Integración con Backend; cierra 008-testing |
| G10 | 009-ci-cd | Pipeline completo y despliegue |

`008-testing` es transversal: sus entregables (contract tests, corpus de seguridad,
cobertura) se acumulan en cada fase y la spec se cierra en G09, junto con
`010-integration-thehouse`, que es la que exige contract tests y E2E en staging.

## Spec activa

Ninguna. La spec `ACTIVE` se declara en la tabla de estado y en el encabezado de su
`spec.md`. Solo una spec puede estar `ACTIVE` a la vez. `002-provider-abstraction` sigue
`PLANNED` hasta que su plan esté aprobado y se marque `ACTIVE`.

## Enmiendas de la constitución

- **Enmienda 1.1 (2026-11-12).** Artículo 8: los estados de una spec son `PLANNED` →
  `ACTIVE` → `IMPLEMENTED` y solo una spec puede estar `ACTIVE` a la vez. Sustituye la
  regla anterior de una sola spec `IMPLEMENTED`. Artículo 5: el adaptador concreto de
  proveedor se define en la spec 011. Registrada en `constitution.md`, sección
  "Enmiendas".

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

## Decisiones de gobernanza (2026-11-12)

- G02 es 100% offline: protocolo `GenerativeAiProvider`, DTOs inmutables, taxonomía de
  errores, `FakeProvider`, factory, timeout obligatorio y límite de entrada. No existe
  adaptador de red en esa fase.
- El adaptador real y la evaluación de proveedores (Gemini, OpenAI, Azure OpenAI) pasan a
  la spec `011-llm-provider` (G03), detrás del mismo puerto.
- El proveedor se elige por precio, capa gratuita, latencia, salida JSON estructurada,
  calidad en español e integración en Python; la decisión queda documentada en la spec.
- Los tests de `011-llm-provider` corren sin red; el smoke test contra una credencial
  real es un script manual opt-in que CI nunca ejecuta.
- `003-smart-match-explanation` incluye autenticación mínima servicio-a-servicio
  (`X-Service-Key`, `SecretStr` en `Settings`, comparación en tiempo constante, 401 con
  el sobre estándar) para cumplir el artículo 7; `005-security` la endurece.
- El mapeo de fases queda en la tabla anterior y `008-testing` se cierra en G09.
- El trabajo se hace en ramas `feature/<spec>` o `chore/<tema>`, nunca en `main`; todo
  merge entra por pull request con squash y con el checklist SDD.

## Contrato de health

```json
{"status": "ok", "service": "thehouse-genai", "version": "0.1.0"}
```

## Configuración futura reservada

`GENAI_PROVIDER`, `GENAI_API_KEY`, `GENAI_MODEL`, `GENAI_TIMEOUT_SECONDS` (15) y
`GENAI_MAX_INPUT_CHARS` (4000). En G01 y G02 no se usan para llamadas externas: 002 solo
los valida y la factory solo admite `fake`; 011 los consume en el adaptador real.

## Evidencia resumida

- `ruff check .`: sin hallazgos.
- `mypy src`: sin errores (strict).
- `pytest`: 21 tests aprobados.
- Commit de bootstrap: `chore: bootstrap generative ai service`.

## Deuda y pendientes

- Definir el puerto `GenerativeAiProvider`, DTOs, errores, fake y factory (002, offline).
- Evaluar proveedores y construir el adaptador real detrás del puerto (011).
- Contratos y guardrails de explicación (003) y parseo (004).
- Auth mínima de servicio en 003; endurecimiento, PII y prompt injection en 005.
- Moderación, observabilidad avanzada, contract tests e integración (006–010).
- No hay despliegue ni credenciales reales configuradas.

## Próximo paso

Aprobar la enmienda 1.1 y el plan de `002-provider-abstraction`; marcarla `ACTIVE` e
implementar G02 sin red, sin adaptador y sin proveedor real.
