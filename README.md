# TheHouse GenAI

Servicio independiente de IA generativa de TheHouse. Recibe contexto ya calculado por
TheHouse Backend, invoca a un proveedor LLM desacoplado y devuelve texto o filtros
estructurados. No calcula Smart Match, no consulta propiedades y no sustituye al Backend.

## Estado

G01 Foundation y G02 (`002-provider-abstraction`) implementados. G02 define el puerto
`GenerativeAiProvider`, sus DTOs inmutables, la taxonomía de errores, el guard central
de timeout y límite de entrada, un `FakeProvider` determinista y la factory de
selección: todo offline, sin sockets y sin proveedor real. El roadmap por fases
(G01–G10) y el estado de cada spec están en `memoria.md`. El proveedor LLM real y los
contratos de IA (`explain-match`, `parse-search`) siguen planificados en `specs/` y
todavía no se implementan.

## Ejecución local

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
uvicorn thehouse_genai.main:app --reload
```

Health probes:

```text
GET http://127.0.0.1:8000/health/live
GET http://127.0.0.1:8000/health/ready
```

## Calidad

```bash
ruff check .
mypy src
pytest
```

## Documentación de proyecto

- `constitution.md`: principios no negociables.
- `AGENTS.md`: reglas de trabajo para agentes.
- `memoria.md`: estado y decisiones acumuladas.
- `specs/001-foundation` a `specs/011-llm-provider`: SDD por incremento.
