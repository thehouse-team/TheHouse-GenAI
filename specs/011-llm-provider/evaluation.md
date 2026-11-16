# Evaluación de proveedores LLM — 011-llm-provider

- **Estado:** ACTIVE
- **Fecha:** 2026-11-15
- **Alcance:** Gemini API (Google AI Studio), OpenAI API y Azure OpenAI, comparados con
  los seis criterios de `spec.md` (RF-01).
- **Método:** cada dato lleva la fuente consultada el 2026-11-15. Los datos sin fuente
  pública citable (latencia y calidad en español) se marcan «pendiente de medir» y se
  medirán con `scripts/smoke_provider.py`; el resultado se registra en `evidence.md` y
  se refleja en esta matriz al cerrar la spec.

## Matriz comparativa

| Criterio | Gemini API (Google AI Studio) | OpenAI API | Azure OpenAI |
| --- | --- | --- | --- |
| Precio por millón de tokens | Paid tier bajo para la familia Flash. La cifra depende del id exacto del modelo y del tamaño de contexto, que aún no está fijado (se fija con `GENAI_MODEL`, sin valor por defecto en el repositorio). Fuente: https://ai.google.dev/gemini-api/docs/pricing | Modelos pequeños de bajo coste por token. Fuente: https://developers.openai.com/api/docs/pricing | No evaluable con la suscripción actual: no se permite crear el recurso. Fuente: https://learn.microsoft.com/en-us/answers/questions/5823985/azure-student-foundry-issue |
| Capa gratuita disponible | Sí, recurrente (Free tier con proyecto activo de AI Studio), con límites por modelo y sin tope de gasto. En la capa gratuita el contenido enviado se usa para mejorar productos de Google; en la de pago, no. Fuentes: https://ai.google.dev/gemini-api/docs/pricing y https://ai.google.dev/gemini-api/docs/billing | No hay capa gratuita. Fuente: https://developers.openai.com/api/docs/pricing | No hay capa gratuita y, además, no se puede crear el recurso. Fuente: https://learn.microsoft.com/en-us/answers/questions/5823985/azure-student-foundry-issue |
| Latencia típica | Pendiente de medir (smoke test manual, bloque B8) | Pendiente de medir | Pendiente de medir (sin recurso) |
| Salida JSON estructurada nativa | Sí: `generationConfig.responseMimeType = application/json` en `generateContent`. Fuente: https://ai.google.dev/api/generate-content | Sí: Structured Outputs con `json_schema`. Fuente: https://developers.openai.com/api/docs/guides/structured-outputs | No verificable con la suscripción actual |
| Calidad en español | Pendiente de medir (caso en español del smoke test, bloque B8) | Pendiente de medir | Pendiente de medir |
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

## Datos no citables a día de hoy

| Dato | Motivo | Cómo se cierra |
| --- | --- | --- |
| Latencia típica y p95 | No hay dato público citable por proveedor | Smoke test manual, 3 iteraciones por caso, en el bloque B8 → `evidence.md` |
| Calidad en español | No hay evaluación citable ni reproducible sin credencial | Caso en español del smoke test, revisado a mano, en el bloque B8 → `evidence.md` |
| Precio exacto por millón de tokens | Depende del id final del modelo y del tamaño de contexto | Se fija con `GENAI_MODEL` y se anota la cifra de la fuente de precios el día del cierre |
| Límites concretos del modelo | Dependen del proyecto y del *usage tier* | Se leen en AI Studio con la credencial de desarrollo |
