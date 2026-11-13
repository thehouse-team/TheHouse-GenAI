# TheHouse GenAI

Servicio independiente de IA generativa de TheHouse. Recibe contexto ya calculado por
TheHouse Backend, invoca a un proveedor LLM desacoplado y devuelve texto o filtros
estructurados. No calcula Smart Match, no consulta propiedades y no sustituye al Backend.

## Estado

G01 Foundation implementado. El roadmap por fases (G01–G10) y el estado de cada spec
están en `memoria.md`. Ninguna spec nueva está `ACTIVE`: el proveedor LLM real y los
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
