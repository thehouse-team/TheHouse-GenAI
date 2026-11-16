# Decisión de proveedor LLM — 011-llm-provider

- **Estado:** ACTIVE
- **Fecha:** 2026-11-15
- **Elegido:** **Gemini API (Google AI Studio)**, familia Flash, por **REST** con
  `httpx` y sin SDK nuevo. El id del modelo se fija con `GENAI_MODEL`; no se
  hardcodea ningún id en el código.
- **Descartados:** OpenAI API y Azure OpenAI.
- **Matriz comparativa:** `evaluation.md`.

## Motivo de la elección

| Criterio | Por qué decide |
| --- | --- |
| Acceso | Es el único candidato accesible con la suscripción actual: Azure OpenAI está bloqueado (probado) y OpenAI exigiría pago desde la primera llamada. |
| Capa gratuita | Free tier recurrente con límites por modelo: permite desarrollo y smoke test sin gastar. Es la diferencia frente a OpenAI. |
| Coste | El paid tier de la familia Flash es de bajo coste por token y solo se activa cuando hace falta. |
| Salida JSON | `generationConfig.responseMimeType = application/json` cubre el requisito de salida estructurada sin SDK. |
| Latencia y calidad en español | **No decisivas hoy**: no hay datos citables. Se miden con el smoke test manual y se revisan en el cierre (ver «Condiciones de revisión»). |

## Alternativas descartadas

### OpenAI API

- **Motivo:** no hay capa gratuita; el coste por token se paga desde la primera
  llamada. Fuente: https://developers.openai.com/api/docs/pricing
- **Se mantiene como primera alternativa** si la calidad en español o la latencia
  medida de Gemini no dan el nivel exigido, o si la política de datos de la capa
  gratuita de Google se vuelve incompatible con el producto.

### Azure OpenAI

- **Motivo:** probado en nuestra suscripción Azure for Students y **no se permite crear
  el recurso**. Fuente:
  https://learn.microsoft.com/en-us/answers/questions/5823985/azure-student-foundry-issue
- **Se revisa** si la suscripción se habilita: aporta identidad corporativa y control
  de residencia de datos, a cambio de más configuración (endpoint, versión de API y
  despliegue).

## Decisiones de integración

| # | Decisión | Alternativa descartada | Motivo |
| --- | --- | --- | --- |
| D-1 | El `400` del vendor se mapea a `ProviderInvalidResponseError` | Crear una clase nueva en `providers/base.py` | Reutilizar la taxonomía de 002 mantiene estable el contrato del puerto y no obliga a tocar `base.py`, que no está en el alcance aprobado de esta spec. |
| D-2 | El `404` (modelo inexistente) se mapea a `ProviderInvalidResponseError` | `ProviderUnavailableError` | Es un fallo no reintentable de configuración, no una indisponibilidad del servicio: `ProviderUnavailableError` es reintentable y induciría reintentos inútiles. |
| D-3 | El timeout de `httpx` es igual a `GENAI_TIMEOUT_SECONDS`, además del timeout total que aplica `GuardedProvider` | Un timeout de `httpx` menor que el del guard | Ambos caminos terminan en `ProviderTimeoutError`, de modo que no hay carrera con dos resultados distintos: el guard acota el total de la llamada y `httpx` acota cada fase. |
| D-4 | La allowlist del logging JSON se amplía con `provider`, `provider_model`, `error_code`, `duration_ms`, `prompt_chars` y `completion_chars` | No registrar el modelo interno | RF-09 exige registrar el modelo y su versión solo en logs internos. Los campos son metadatos y longitudes: nunca contenido, ni prompts, ni respuestas, ni cabeceras. |
| D-5 | El adaptador vive en `src/thehouse_genai/providers/gemini.py` | `providers/gemini_provider.py` | Coherencia con `providers/fake.py` y `providers/factory.py`, y con la excepción de la frontera de imports, que se indexa por ruta. |
| D-6 | El cliente `httpx` se crea por llamada | Cliente compartido con pool de conexiones | No deja un ciclo de vida pendiente de cerrar ni obliga a ampliar el puerto con un hook de cierre. El coste en latencia se mide en el smoke test y se revisa en 007 si resulta significativo. |
| D-7 | `temperature` se envía siempre, aunque algunas familias de Gemini lo ignoren | Omitirlo cuando el modelo no lo soporte | El puerto expone la temperatura como parámetro del contrato; omitirla silenciosamente mentiría sobre ese contrato. El smoke test registra las cabeceras de deprecación que devuelva el vendor. |
| D-8 | La política de capas es: smoke test de 011 en la capa gratuita con prompts sintéticos; proyecto de pago con tope de gasto antes de la demo con datos reales | Usar la capa gratuita para todo | En la capa gratuita el contenido enviado se usa para mejorar productos de Google (fuente: https://ai.google.dev/gemini-api/docs/billing). Por fases: el bloque B8 de esta spec (G03) se ejecuta en la capa gratuita con prompts sintéticos; el proyecto de pago con tope de gasto y alarma de presupuesto se crea **antes de la demo con datos reales, en la fase G09**. |
| D-9 | No hay modelo por defecto en el repositorio; `GENAI_MODEL` vacío significa «no configurado» | Fijar un id de Flash en `.env.example` o en el código | Google renombra y retira ids; el id se decide en el despliegue, sin cambios de código. Con proveedor `gemini`, un `GENAI_MODEL` vacío es un error de configuración. |
| D-10 | `GENAI_TIMEOUT_SECONDS` mantiene el valor por defecto de 15 s | Subir el valor por defecto a 30 s | Es el valor heredado de 001 y 002, con el guard central ya acotando la llamada. Se puede subir por entorno si el smoke test muestra que 15 s es insuficiente. |
| D-11 | El adaptador no valida que el JSON devuelto parsea | Validar el JSON en el adaptador | El puerto devuelve texto y el esquema de negocio lo validan 003 y 004; validarlo aquí duplicaría lógica y adelantaría alcance de negocio. |
| D-12 | La spec no se cierra como `IMPLEMENTED` sin un smoke test real ejecutado y registrado en `evidence.md` | Cerrar la spec con la evidencia del código | Los criterios de aceptación incluyen el script documentado y fuera de CI, pero la latencia y la calidad en español de la matriz solo existen si el script se ejecuta con una credencial real. |
| D-13 | La factory incorpora `ProviderConfigurationError`, subclase de `ValueError` ajena a la taxonomía `ProviderError` | Reutilizar `UnsupportedProviderError` | «Proveedor no soportado» y «credencial o modelo ausentes» son fallos de configuración distintos; reutilizar el segundo error daría un mensaje engañoso. |
| D-14 | `GENAI_PROVIDER` sin definir sigue lanzando `UnsupportedProviderError`; no hay proveedor por defecto | Usar `fake` como valor por defecto | Se mantiene la doble barrera de 002 (D-14): la configuración inválida falla de forma explícita y la factory nunca inventa un proveedor. |

## Integración acordada

- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.
- Credencial: cabecera `x-goog-api-key`, nunca en la URL ni en el body.
- Body: `systemInstruction` desde el system prompt, `contents` con el prompt del
  usuario, `generationConfig` con `temperature`, `maxOutputTokens` y
  `responseMimeType` (`application/json` cuando el formato de respuesta es JSON).
- Respuesta: `candidates[0].content.parts[*].text` como texto, `usageMetadata` como
  uso, `candidates[0].finishReason` como motivo de fin y `modelVersion` como metadato
  interno del modelo.
- Errores: `400` y `404` a `ProviderInvalidResponseError`; `401` y `403` a
  `ProviderAuthError`; `408` a `ProviderTimeoutError`; `429` a
  `ProviderRateLimitError`; `5xx` a `ProviderUnavailableError`; timeout de `httpx` a
  `ProviderTimeoutError`; error de red a `ProviderUnavailableError`; respuesta
  bloqueada o vacía a `ProviderInvalidResponseError`.
- El cuerpo de la respuesta del vendor nunca se incluye en una excepción: la taxonomía
  de 002 no admite detalle, de modo que no hay por dónde filtrarlo.

## Uso previsto y política de datos

- **Desarrollo y smoke test (G03, bloque B8):** capa gratuita, prompts sintéticos,
  sin datos reales ni PII.
- **Antes de la demo con datos reales (G09):** capa de pago con tope de gasto y alarma
  de presupuesto en el proyecto de Google Cloud. En la capa de pago el contenido no se
  usa para mejorar productos de Google (fuente:
  https://ai.google.dev/gemini-api/docs/billing).
- La allowlist de campos que se envía al provider se define en 003, 004 y 005: esta
  spec no decide qué contexto se envía, solo cómo se transporta.

## Condiciones de revisión

1. **Precios o límites** de Gemini cambian → reevaluar la matriz y confirmar que
   Gemini sigue ganando (fuentes: pricing, billing y rate limits de la documentación
   de la API).
2. **Acceso a Azure** habilitado en la suscripción → reevaluar Azure OpenAI.
3. **Latencia medida** por encima del umbral acordado o **calidad en español**
   insuficiente → reevaluar OpenAI API.
4. **Cambio de API**: si `generateContent` se marca como heredada o deprecada →
   migrar el adaptador a la Interactions API. El puerto no cambia: solo cambia
   `providers/gemini.py`.
5. **Cambio en el modelo elegido**: si la familia Flash deja de estar disponible o
   cambia su política de datos → reevaluar el id de `GENAI_MODEL` y la capa de pago.
6. **Presupuesto**: si el consumo de la capa de pago se acerca al tope → endurecer el
   límite de entrada o pausar el uso.
