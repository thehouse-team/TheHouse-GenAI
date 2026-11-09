# Constitución — TheHouse GenAI

Versión 1.0 · Ratificada 2026-11-08 · Aplica a todo el repositorio.

## Preámbulo

TheHouse GenAI existe para convertir contexto ya validado por TheHouse Backend en
lenguaje natural o filtros estructurados. Es un servicio de IA generativa, no una fuente
de verdad y no un sustituto del Backend. Esta constitución prevalece sobre cualquier
propuesta, tarea o atajo.

## Artículo 1 — Responsabilidad acotada

GenAI solo puede: explicar información recibida, redactar texto y transformar lenguaje
natural en estructuras permitidas. No consulta propiedades, no calcula Smart Match, no
gestiona autenticación, no contiene Mobile y no reemplaza al Backend.

## Artículo 2 — Separación ML / GenAI

El Smart Match se calcula exclusivamente en la capa ML/Backend. GenAI recibe el score y
los hechos relevantes ya calculados. GenAI puede explicar el resultado; nunca calcularlo,
recalcularlo, corregirlo ni presentarlo como propio.

## Artículo 3 — Verdad de los datos

GenAI no puede inventar ni modificar `score`, `price`, `distance`, `services`,
`property`, `university` ni `availability`. Todo hecho mostrado al usuario debe provenir
del contexto de entrada. Si un dato falta o es inconsistente, la respuesta se rechaza o
se degrada de forma segura; no se completa por inferencia.

## Artículo 4 — Privacidad y secretos

Los secretos viven fuera del repositorio. Nunca se envían al cliente, no se registran en
logs y no se incluyen en prompts. GenAI recibe el mínimo de PII necesario y jamás:
passwords, access/refresh tokens, dirección exacta, datos privados del propietario o PII
no requerida por el caso de uso. Los logs son estructurados y no contienen cuerpos,
cabeceras sensibles ni credenciales.

## Artículo 5 — Proveedor desacoplado

Toda capacidad LLM se consume a través de una interfaz propia (spec 002). La capa de
aplicación no conoce SDKs ni formatos de proveedor. El proveedor real es reemplazable y
las pruebas usan un doble de test; nunca se depende de la red en CI.

## Artículo 6 — Contratos explícitos

Los endpoints tienen contratos versionados y validados con Pydantic. Los errores usan un
único sobre `{"error": {"code", "message", "request_id"}}`. No se exponen stack traces,
detalles internos ni mensajes de proveedor al cliente. Toda llamada externa tiene timeout
y tamaño de entrada limitado.

## Artículo 7 — Seguridad desde el día uno

Límite de tamaño de request, CORS restrictivo y configurable, validación estricta de
configuración al arrancar, autenticación servicio-a-servicio antes de exponer endpoints
generativos, y defensa contra prompt injection. Un fallo de seguridad bloquea el avance
de la spec.

## Artículo 8 — Spec Driven Development

Cada incremento vive en `specs/NNN-*` con `spec.md`, `plan.md`, `task.md`, `checklist.md`
y `evidence.md`. No se implementa una spec sin plan aprobado ni se cierra sin evidencia.
Solo una spec puede estar `IMPLEMENTED` a la vez; el resto permanece `PLANNED` hasta su
turno. Este repositorio arranca con `001-foundation` como única spec implementada.

## Artículo 9 — Stack y simplicidad

Python 3.12+, FastAPI, Pydantic, Uvicorn, httpx, pytest, ruff y mypy. Sin Docker en este
repositorio. Capas: `api/`, `application/`, `domain/`, `providers/`, `infrastructure/`.
Se prefiere la solución más pequeña que cumpla el contrato y pueda probarse.

## Artículo 10 — Calidad y CI

`ruff check .`, `mypy src` y `pytest` son obligatorios y bloqueantes. El CI replica esos
gates. No se hace commit con gates en rojo. No hay CD ni despliegue en G01.

## Cumplimiento

Una contribución que viole cualquier artículo debe rechazarse aunque funcione. Las
excepciones requieren una enmienda explícita de esta constitución y quedan registradas en
`memoria.md`.
