# TheHouse GenAI

Servicio independiente de IA generativa de TheHouse. Recibe contexto ya calculado por
TheHouse Backend, invoca a un proveedor LLM desacoplado y devuelve texto o filtros
estructurados. No calcula Smart Match, no consulta propiedades y no sustituye al Backend.

## Estado

G01 Foundation, G02 (`002-provider-abstraction`) y G03 (`011-llm-provider`)
implementados. **G04 (`003-smart-match-explanation`) en curso.**

G02 define el puerto `GenerativeAiProvider`, sus DTOs inmutables, la taxonomía de
errores, el guard central de timeout y límite de entrada, un `FakeProvider`
determinista y la factory de selección: todo offline, sin sockets y sin proveedor real.

G03 eligió y conectó el proveedor real: **Gemini API (Google AI Studio)**, familia
Flash, por REST con `httpx` y sin SDK nuevo, detrás del mismo puerto. La matriz
comparativa con sus fuentes está en `specs/011-llm-provider/evaluation.md` y la
decisión, con las alternativas descartadas y las condiciones de revisión, en
`specs/011-llm-provider/decision.md`. En desarrollo se usó `gemini-3.5-flash-lite` en
la capa gratuita, con prompts sintéticos.

El roadmap por fases (G01–G10) y el estado de cada spec están en `memoria.md`. El
contrato de `explain-match` está aprobado con Backend y se implementa en G04;
`parse-search` sigue planificado en `specs/` y todavía no se implementa.

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

## Proveedor LLM

El proveedor real es **Gemini API (Google AI Studio)**, familia Flash, y se invoca
por REST con `httpx`. Su configuración es por entorno:

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `GENAI_PROVIDER` | Sí | `fake` (doble de test, sin red) o `gemini` |
| `GENAI_API_KEY` | Con `gemini` | Credencial; se modela como `SecretStr` y nunca se registra |
| `GENAI_MODEL` | Con `gemini` | Id del modelo; no hay valor por defecto en el repositorio |
| `GENAI_TIMEOUT_SECONDS` | No | Timeout de la llamada; 15 s por defecto |
| `GENAI_MAX_INPUT_CHARS` | No | Límite de entrada; 4000 caracteres por defecto |

El script `scripts/smoke_provider.py` es una utilidad **manual y opt-in** para
validar una credencial real: no lo ejecuta CI y nunca imprime la clave. Se ejecuta
con la capa gratuita y prompts sintéticos:

```bash
python scripts/smoke_provider.py --i-have-a-real-key
```

El script pide una confirmación escrita (`SI`, o `--yes` para omitirla), mide la
latencia de dos casos (texto en español y salida JSON) e imprime una tabla resumen
lista para `specs/011-llm-provider/evidence.md`. Si la variable `CI` está activa,
sale con código 2 sin hacer nada.
