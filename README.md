# TheHouse GenAI

Servicio independiente de IA generativa de TheHouse. Recibe contexto ya calculado por
TheHouse Backend, invoca a un proveedor LLM desacoplado y devuelve texto o filtros
estructurados. No calcula Smart Match, no consulta propiedades y no sustituye al Backend.

## Estado

G01 Foundation, G02 (`002-provider-abstraction`), G03 (`011-llm-provider`) y G04
(`003-smart-match-explanation`) implementados. G05 (`005-security`) está en curso:
endurece la autenticación de servicio de 003 con rotación de clave, rate limiting,
allowlist de PII, corpus de inyección y logging de seguridad, sin cambiar el contrato de
`explain-match`.

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

## Endpoint explain-match

`POST /api/v1/generative/explain-match`. Requiere la cabecera `X-Service-Key` con el
secreto compartido con Backend (configurado en `GENAI_SERVICE_KEY`); sin clave o con una
clave inválida responde `401` con el sobre de error estándar. La autenticación se evalúa
antes de validar el body. Durante la rotación se aceptan dos claves: la actual
(`GENAI_SERVICE_KEY`) y la anterior (`GENAI_SERVICE_KEY_PREVIOUS`); si no hay clave
actual, el servicio falla cerrado. El acceso se limita por cliente a 60 peticiones por
minuto en memoria del proceso, con `429` y `Retry-After` al excederse. mTLS queda fuera
de alcance y se decide en G09/G10.

Request (camelCase, campos obligatorios salvo `locale` y las listas de servicios):

```json
{
  "matchScore": 91,
  "locale": "es-MX",
  "university": "UTTT",
  "property": {
    "title": "Habitación cerca de UTTT",
    "price": 2800,
    "currency": "MXN",
    "distanceKm": 1.3,
    "services": ["internet"]
  },
  "preferences": {
    "budgetMax": 3000,
    "currency": "MXN",
    "maxDistanceKm": 3.0,
    "essentialServices": ["internet"]
  }
}
```

Response:

```json
{
  "explanation": "Habitación cerca de UTTT coincide un 91% porque cuesta $2,800 MXN, se ubica a 1.3 kilómetros de la universidad y cuenta con internet.",
  "generated": true,
  "promptVersion": "explain_match_v3"
}
```

`generated=false` indica una explicación de plantilla construida solo con datos del
input (fallo del proveedor o salida rechazada); en ese caso el código HTTP sigue siendo
`200`. GenAI no calcula ni modifica `matchScore` y nunca devuelve detalles del proveedor.
Ver `specs/003-smart-match-explanation/evidence.md` para las pruebas reales.

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
| `GENAI_SERVICE_KEY` | Sí, para `explain-match` | Secreto compartido con Backend (`X-Service-Key`); `SecretStr`, nunca se registra |
| `GENAI_SERVICE_KEY_PREVIOUS` | No | Clave anterior durante la rotación; deja de aceptarse al retirarla. Vacía o en blanco se normaliza a `None` |
| `GENAI_API_KEY` | Con `gemini` | Credencial; se modela como `SecretStr` y nunca se registra |
| `GENAI_MODEL` | Con `gemini` | Id del modelo; no hay valor por defecto en el repositorio |
| `GENAI_TIMEOUT_SECONDS` | No | Timeout de la llamada; 15 s por defecto. En producción (G09/G10) usar 6 s y 8 s en el cliente de Backend (D18) |
| `GENAI_MAX_INPUT_CHARS` | No | Límite de entrada; 4000 caracteres por defecto |
| `GENAI_RATE_LIMIT_ENABLED` | No | Rate limit en memoria; `true` por defecto |
| `GENAI_RATE_LIMIT_REQUESTS` | No | Peticiones por ventana y cliente; 60 por defecto |
| `GENAI_RATE_LIMIT_WINDOW_SECONDS` | No | Duración de la ventana; 60 s por defecto |
| `GENAI_RATE_LIMIT_MAX_CLIENTS` | No | Máximo de ventanas rastreadas; 1000 por defecto |

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
