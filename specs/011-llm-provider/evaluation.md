# Evaluación de proveedores LLM — 011-llm-provider

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-15 (mediciones del 2026-11-16)
- **Alcance:** Gemini API (Google AI Studio), OpenAI API y Azure OpenAI, comparados con
  los seis criterios de `spec.md` (RF-01).
- **Método:** cada dato lleva la fuente consultada el 2026-11-15. Los dos criterios
  que no tienen fuente pública citable (latencia y calidad en español) se midieron el
  2026-11-16 con `scripts/smoke_provider.py` en la capa gratuita; el resultado está en
  `evidence.md` y se refleja en esta matriz. OpenAI y Azure quedan «no medido»: no
  hay acceso a ellos con la suscripción actual.

## Matriz comparativa

| Criterio | Gemini API (Google AI Studio) | OpenAI API | Azure OpenAI |
| --- | --- | --- | --- |
| Precio por millón de tokens | Paid tier bajo para la familia Flash. La cifra depende del id exacto del modelo, que en desarrollo fue `gemini-3.5-flash-lite`; el precio por millón de tokens de ese id queda por anotar desde la fuente de precios. Fuente: https://ai.google.dev/gemini-api/docs/pricing | Modelos pequeños de bajo coste por token. Fuente: https://developers.openai.com/api/docs/pricing | No evaluable con la suscripción actual: no se permite crear el recurso. Fuente: https://learn.microsoft.com/en-us/answers/questions/5823985/azure-student-foundry-issue |
| Capa gratuita disponible | Sí, recurrente (Free tier con proyecto activo de AI Studio), con límites por modelo y sin tope de gasto. En la capa gratuita el contenido enviado se usa para mejorar productos de Google; en la de pago, no. Fuentes: https://ai.google.dev/gemini-api/docs/pricing y https://ai.google.dev/gemini-api/docs/billing | No hay capa gratuita. Fuente: https://developers.openai.com/api/docs/pricing | No hay capa gratuita y, además, no se puede crear el recurso. Fuente: https://learn.microsoft.com/en-us/answers/questions/5823985/azure-student-foundry-issue |
| Latencia típica | **Medida** el 2026-11-16 con `gemini-3.5-flash-lite` en capa gratuita: 817.0 ms el mínimo, 1461.3 ms el máximo, medianas de 1047.4 ms (JSON) y 1445.0 ms (texto) en 3 iteraciones por caso. Detalle en `evidence.md`. | No medido | No medido (sin recurso) |
| Salida JSON estructurada nativa | Sí: `generationConfig.responseMimeType = application/json` en `generateContent`. Fuente: https://ai.google.dev/api/generate-content | Sí: Structured Outputs con `json_schema`. Fuente: https://developers.openai.com/api/docs/guides/structured-outputs | No verificable con la suscripción actual |
| Calidad en español | **Medida** el 2026-11-16 con `gemini-3.5-flash-lite`: español natural, solo con los datos del prompt y sin inventar hechos (único defecto: un espacio faltante, "conuna"). La salida JSON fue válida y con los cinco campos pedidos. | No medido | No medido |
| Integración oficial en Python | Sí: SDK oficial `google-genai` (`from google import genai`). En esta spec **no** se usa el SDK: adaptador REST con `httpx`. Fuente: https://ai.google.dev/gemini-api/docs/text-generation | Sí: SDK oficial `openai`. Fuente: https://github.com/openai/openai-python | No verificable con la suscripción actual |

## Límites operativos

Contexto para el coste y para la latencia esperable:

- Los límites se aplican **por proyecto y por modelo** (requests por minuto, tokens por
  minuto y requests por día) y dependen del *usage tier*. El tier Free no tiene límite
  de gasto; los tiers de pago tienen un tope de gasto por ventana de 10 minutos que
  devuelve `429 RESOURCE_EXHAUSTED`.
  Fuente: https://ai.google.dev/gemini-api/docs/rate-limits
- El límite concreto de cada modelo no es un valor fijo publicable: se consulta en AI
  Studio con la credencial del proyecto.
  Fuente: https://ai.google.dev/gemini-api/docs/rate-limits

## Hallazgos de documentación que condicionan la integración

- Gemini 4 y Gemini 3.6+ **ignoran** los valores de `temperature`, `top_p` y `top_k` y
  devuelven cabeceras de deprecación.
  Fuente: https://ai.google.dev/gemini-api/docs/text-generation
- La documentación de generación de texto lidera hoy con la *Interactions API*
  (`POST /v1beta/interactions`), mientras que `generateContent`
  (`POST /v1beta/models/{model}:generateContent`) sigue documentado y es el endpoint
  que usa este adaptador.
  Fuentes: https://ai.google.dev/gemini-api/docs/text-generation y
  https://ai.google.dev/api/generate-content

## Datos medidos y datos aún pendientes

| Dato | Estado | Fuente o método |
| --- | --- | --- |
| Latencia típica y p95 | **Medida** el 2026-11-16: 817.0 ms el mínimo y 1461.3 ms el máximo en seis llamadas con `gemini-3.5-flash-lite` en capa gratuita. El p95 no se puede calcular con tres iteraciones por caso. | Smoke test manual → `evidence.md` |
| Calidad en español | **Medida** el 2026-11-16: español natural, sin datos inventados, con un único defecto menor de espaciado; JSON válido con los cinco campos pedidos. | Smoke test manual → `evidence.md` |
| Precio exacto por millón de tokens | Pendiente: depende del id final del modelo. En desarrollo se usó `gemini-3.5-flash-lite`. | Se anota desde la fuente de precios el día del cierre |
| Límites concretos del modelo | **Leídos** el 2026-11-16 en AI Studio para la capa gratuita del proyecto `thehouse-genai`: ~15 RPM, 250K TPM y 500 RPD. | https://ai.google.dev/gemini-api/docs/rate-limits y AI Studio |
