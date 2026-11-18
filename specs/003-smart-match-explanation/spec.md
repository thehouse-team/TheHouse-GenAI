# 003-smart-match-explanation — Explicación de Smart Match

- **Estado:** IMPLEMENTED
- **Depende de:** 001-foundation, 002-provider-abstraction, 011-llm-provider
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08
- **Última revisión:** 2026-11-17

## Objetivo

Explicar en lenguaje natural un match score calculado externamente, usando solo los hechos y preferencias entregados por TheHouse Backend, sin alterar ningún dato.

## Contexto

Smart Match es una función ML del Backend. GenAI no lo calcula. El endpoint recibe el score ya calculado y datos reales de propiedad/preferencias para redactar una explicación breve y fiel. G04 implementa este contrato detrás del puerto `GenerativeAiProvider` de 002/011.

## Alcance

### Incluido

- Contrato HTTP `POST /api/v1/generative/explain-match`, camelCase en el alambre con
  aliases sobre modelos Python snake_case (`extra="forbid"`).
- Validación de `matchScore`, propiedad, universidad (`str`), preferencias mínimas,
  `locale` (solo `es-MX`) y coherencia de monedas.
- Precios y presupuesto como `Decimal` (ge 0, máximo 2 decimales); formato es-MX en la
  explicación sin inventar conversión de moneda.
- Prompt versionado `explain_match_v3` (v1 y v2 quedan como históricas), con datos no
  confiables delimitados y escapados; segunda persona, tono cálido, 2–3 oraciones,
  máximo 60 palabras, porcentaje con `%`, precios `$2,800 MXN`, sin saludos ni
  exclamaciones y sin la expresión «por ciento».
- Normalización determinista de espacios antes de validar (corrección tipográfica que
  no altera hechos).
- Validación de salida: longitud máxima 60 palabras, sin números ausentes del input,
  porcentaje igual a `matchScore`, servicios del vocabulario permitido, sin datos
  inventados y sin palabras pegadas (`MALFORMED_TEXT`).
- Respuesta `{explanation, generated, promptVersion}`; el score no se devuelve ni se
  modifica y nunca se exponen `provider_model` ni detalles del proveedor.
- Fallback seguro: `generated=false` con plantilla neutra y factual construida solo
  con datos del input; el fallback no es un error para el Backend.
- Autenticación mínima servicio-a-servicio: header `X-Service-Key`, credencial en
  `Settings` como `SecretStr` (env `GENAI_SERVICE_KEY`), comparación en tiempo constante
  y `401` con el sobre de error estándar.
- Pruebas con fake provider e intentos de prompt injection, 100% sin red.

### Excluido

- Cálculo o recálculo de Smart Match.
- Consulta de propiedades, precios, distancias o disponibilidad.
- Dirección exacta, datos del propietario o PII innecesaria.
- Proveedor real y despliegue.
- Autenticación de usuarios finales, mTLS, rotación de secretos y rate limiting (spec
  005).

## Requisitos

- **RF-01:** `matchScore` es obligatorio, entero 0–100 y se recibe ya calculado.
- **RF-02:** la explicación solo puede citar hechos de la allowlist de entrada.
- **RF-03:** no se inventan precios, distancias, servicios, universidad ni disponibilidad.
- **RF-04:** la salida no incluye un score propio ni modificado. El modelo puede
  mencionar el porcentaje recibido solo si es idéntico a `matchScore` (D3).
- **RF-05:** la explicación tiene un máximo de 60 palabras en `explain_match_v3`
  (120 en `explain_match_v1`, 60 en `explain_match_v2`, ambas históricas).
- **RF-06:** entradas inconsistentes o incompletas se rechazan con 422. En particular,
  `property.currency != preferences.currency` es 422 (D9).
- **RF-07:** texto libre de propiedad se trata como dato, no como instrucción.
- **RF-08:** el endpoint exige el header `X-Service-Key`; sin credencial válida responde
  401 con `{"error": {"code", "message", "request_id"}}`.
- **RF-09:** la credencial se compara en tiempo constante y nunca se registra.
- **RF-10:** el contrato HTTP usa camelCase (`matchScore`, `distanceKm`, `budgetMax`,
  `essentialServices`, `maxDistanceKm`, `promptVersion`) con aliases sobre modelos
  Python snake_case y `extra="forbid"` (D1).
- **RF-11:** la respuesta es exactamente `{explanation, generated, promptVersion}`; no
  se devuelve `facts_used`, score, uso ni metadatos del proveedor (D2).
- **RF-12:** `locale` es opcional con valor por defecto `es-MX`; cualquier otro valor se
  rechaza con 422 (D6).
- **RF-13:** `university` es `str` (D7). `price` y `budgetMax` son `Decimal` con ge 0 y
  máximo 2 decimales (ajuste 4).
- **RF-14:** `promptVersion` es una constante propia (`explain_match_v3`); nunca se
  deriva de `provider_model` ni de otro detalle del proveedor.
- **RF-15:** ante fallo del proveedor, timeout o rechazo de la validación, se responde
  **200** con `generated=false` y la plantilla de fallback; no se devuelve 502 (D4).
- **RF-16:** la plantilla de fallback es neutra y factual, no dice «No se pudo generar»,
  y atribuye la coincidencia a las preferencias del estudiante, no a la universidad
  (ajuste 3).
- **RF-17:** la credencial de servicio se configura con `GENAI_SERVICE_KEY` como
  `SecretStr | None`; vacía o solo espacios se normaliza a `None` y la auth falla cerrado
  (D8).
- **RF-18:** los servicios solo se validan contra caracteres de control y longitud
  máxima de 40; no se aplica regex restrictiva y los delimitadores se escapan en
  `to_context()` (ajuste 5).
- **RF-19:** `explain_match_v3` habla en segunda persona con tono cálido, usa 2–3
  oraciones y máximo 60 palabras, escribe el porcentaje con el símbolo `%` (no «por
  ciento») y los precios como `$2,800 MXN` con la moneda del input, evita «el resultado
  de coincidencia es» y «puntaje», no saluda ni usa exclamaciones y empieza directo con
  la propiedad (D15, D17).
- **RF-20:** palabras pegadas como `delpresupuesto` o `conuna` se rechazan con
  `MALFORMED_TEXT` y degradan a fallback; el detector es acotado y evita falsos
  positivos con palabras válidas (D14).
- **RF-21:** el logger `httpx` se configura en WARNING para conservar solo los logs
  estructurados propios (D16).
- **RF-22:** antes de validar se normalizan solo espacios: después de `, ; : ! ?` y de
  un punto que cierra oración seguido de letra (sin tocar `1.3` ni `2,800`), entre letra
  y `$`, se colapsan espacios múltiples y se aplica `strip`. No se cambia ninguna palabra
  ni número; es una corrección tipográfica, no una alteración de hechos (D17).

## Criterios de aceptación

- [ ] Contrato request/response documentado y validado (camelCase con aliases).
- [ ] Explicación de fixture cita solo hechos permitidos.
- [ ] Se rechazan números y servicios ausentes en la entrada.
- [ ] Un porcentaje distinto de `matchScore` se rechaza y degrada a fallback.
- [ ] `delpresupuesto` y `conuna` se rechazan con `MALFORMED_TEXT`, sin marcar
      palabras válidas como `porque` o `conde`.
- [ ] Las respuestas reales de Gemini se usan como fixtures: la normal se acepta y la
      de `delpresupuesto` degrada a fallback.
- [ ] `91%`, `$2,800 MXN` y `$3,000 MXN` pasan la validación de números (D13).
- [ ] `promptVersion` es `explain_match_v3` y el prompt incluye sus nuevas reglas.
- [ ] La normalización corrige `cuesta$2,800` y `1.3 km,estando` sin alterar `1.3`,
      `2,800`, `$3,000 MXN` ni `91%`; «91 por ciento» se acepta.
- [ ] `delpresupuesto` sigue degradando a `MALFORMED_TEXT`.
- [ ] El logger `httpx` queda en WARNING.
- [ ] Prompt injection en título, universidad y servicios (incluido `</untrusted_data>`)
      no cambia reglas ni hechos.
- [ ] Score faltante o fuera de rango devuelve 422.
- [ ] `locale` distinto de `es-MX` y monedas dispares devuelven 422.
- [ ] `price` y `budgetMax` rechazan más de 2 decimales.
- [ ] Pruebas con fake provider, sin red.
- [ ] No existe acceso a base de datos ni a propiedades.
- [ ] Fallo/timeout del proveedor y salida rechazada devuelven 200 con
      `generated=false` y plantilla neutra (nunca 502).
- [ ] `provider_model` y cualquier detalle del proveedor no aparecen en la respuesta.
- [ ] Endpoint sin `X-Service-Key` devuelve 401 con el sobre estándar.
- [ ] `X-Service-Key` incorrecto devuelve 401 sin revelar si la credencial existe.
- [ ] La credencial no aparece en logs ni en el `repr` de `Settings`.

## Seguridad y privacidad

- Minimizar PII: sin nombre de propietario, dirección exacta ni tokens.
- No registrar prompt ni explicación completos por defecto.
- Defensa contra prompt injection en todos los campos de texto libre.
- Limitar longitud de entrada y salida.
- Autenticación mínima servicio-a-servicio en esta spec (`X-Service-Key` en `Settings`
  como `SecretStr` desde `GENAI_SERVICE_KEY`, comparación en tiempo constante, 401 con
  el sobre estándar) para cumplir el artículo 7 de la constitución. La spec 005 endurece
  esta autenticación (rotación, mTLS o secreto negociado con Backend, rate limiting y
  filtrado de PII). El proveedor no configurado degrada con log `ERROR`; su readiness se
  decide en 007 (D5).

## Contrato HTTP (aprobado con Backend)

`POST /api/v1/generative/explain-match`. Los nombres camelCase son los que revisa
Backend; internamente se modelan en snake_case con `Field(alias=...)` y
`extra="forbid"` en todos los objetos (D1).

Entrada:

```json
{
  "matchScore": 87,
  "locale": "es-MX",
  "university": "UTTT",
  "property": {
    "title": "Cuarto cerca de UTTT",
    "price": 2800,
    "currency": "MXN",
    "distanceKm": 1.2,
    "services": ["internet", "agua"]
  },
  "preferences": {
    "budgetMax": 3000,
    "currency": "MXN",
    "maxDistanceKm": 2.0,
    "essentialServices": ["internet"]
  }
}
```

- **Obligatorios:** `matchScore`, `university`, `property` (`title`, `price`,
  `currency`, `distanceKm`) y `preferences` (`budgetMax`, `currency`, `maxDistanceKm`).
- **Opcionales:** `locale` (default `es-MX`), `property.services` y
  `preferences.essentialServices` (listas vacías por defecto).
- `matchScore`: entero 0–100. `university`: `str`. `locale`: solo `es-MX`.
- `price` y `budgetMax`: `Decimal` ≥ 0 con máximo 2 decimales.
- `distanceKm` y `maxDistanceKm`: number ≥ 0.
- Si `property.currency != preferences.currency` → 422 (D9). No se inventa conversión.
- Servicios: solo se rechazan caracteres de control y longitud > 40; los delimitadores
  como `<untrusted_data>` se escapan al construir el contexto, no se rechazan.

Salida (exactamente tres campos):

```json
{
  "explanation": "Esta propiedad tiene una coincidencia del 87% con tus preferencias. Cuarto cerca de UTTT cuesta $2,800 MXN, está a 1.2 km de la UTTT y cuenta con internet, agua. Tu presupuesto es de $3,000 MXN.",
  "generated": true,
  "promptVersion": "explain_match_v3"
}
```

- `generated=true`: salida del modelo validada. `generated=false`: plantilla de fallback.
- `promptVersion` es constante del servicio (`explain_match_v3`); nunca se toma de
  `provider_model` ni de otro dato del proveedor.
- El score no se devuelve como campo; solo puede aparecer dentro de `explanation`
  como porcentaje idéntico a `matchScore` (D3).

## Fallback

Si el proveedor falla, agota el timeout o la validación rechaza la salida, se responde
**200** con `generated=false` y esta plantilla neutra y factual, construida solo con
datos del input (ajuste 3):

> Esta propiedad tiene una coincidencia del {matchScore}% con tus preferencias.
> {title} cuesta ${price} {currency}, está a {distanceKm} km de la {university} y cuenta
> con {servicios}. Tu presupuesto es de ${budgetMax} {currency}.

La coincidencia se atribuye a las preferencias del estudiante, **no** a la universidad.
No se usa la frase «No se pudo generar…». El fallback no es un error para Backend.

## Decisiones aprobadas

| # | Decisión |
| --- | --- |
| D1 | Contrato camelCase en HTTP con aliases sobre modelos Python snake_case; `extra="forbid"`. |
| D2 | Sin `facts_used` en la respuesta; queda como artefacto interno del validador. |
| D3 | El modelo puede mencionar el porcentaje, siempre igual a `matchScore` y validado. |
| D4 | Fallo del proveedor o salida rechazada → 200 con `generated=false`; se elimina el 502 del plan. |
| D5 | Proveedor no configurado o fallido: degradar con log `ERROR`; readiness del proveedor se decide en 007. |
| D6 | `locale` restringido a `es-MX`. |
| D7 | `university` es `str`. |
| D8 | `GENAI_SERVICE_KEY` como `SecretStr | None`; vacío o espacios → `None`, auth falla cerrado. |
| D9 | 422 si `property.currency != preferences.currency`. |
| D10 | Medir el tamaño real de system prompt + contexto en B5 antes de decidir si se sube `GENAI_MAX_INPUT_CHARS`. |
| D11 | Alinear `AGENTS.md` y la gobernanza en B1. |
| D12 | Vocabulario inicial de servicios en `domain`: `internet`, `agua`, `luz`, `gas`, `estacionamiento`, `lavadora`, `amueblado`, `baño privado`, `mascotas`. |
| D13 | Normalizar todos los números a decimal antes de compararlos con los del input. |
| D14 | `MALFORMED_TEXT` detecta palabras pegadas con prefijo funcional + sufijo del dominio, coincidencia exacta, sin acentos y allowlist de palabras válidas (`porque`, `conque`, `delimite`). Un regex amplio daría falsos positivos con `conde`, `conforme`, `delante` o `debajo`. |
| D15 | Prompt `explain_match_v2` según las respuestas reales de Gemini: segunda persona, tono cálido, 2–3 oraciones, máximo 60 palabras, porcentaje con `%`, precios `$2,800 MXN`, sin «el resultado de coincidencia es» ni «puntaje», con espacio entre palabras. Queda histórica. |
| D16 | El logger `httpx` se fija en WARNING para conservar solo los logs estructurados propios. |
| D17 | Ante errores de espacio junto a puntuación (`cuesta$2,800`, `1.3 km,estando`) se normaliza en lugar de rechazar: es una corrección tipográfica que no altera hechos. Las reglas exigen letra adyacente, por lo que decimales (`1.3`) y miles (`2,800`) no se tocan. Las palabras pegadas siguen siendo `MALFORMED_TEXT` (D14). Prompt `explain_match_v3`: sin saludos ni exclamaciones, empieza con la propiedad y usa el símbolo `%` en vez de «por ciento». |
| D18 | GenAI debe cortar antes que el Backend. Recomendación de producción: `GENAI_TIMEOUT_SECONDS=6` en GenAI y timeout de 8 s en el cliente del Backend, por el pico real de 9639 ms en la capa gratuita. El default de `Settings` sigue en 15 s; se aplica en G09/G10. |

### Ajustes obligatorios incorporados

1. Regla 4 del system prompt: «no lo completes ni lo deduzcas» (sin caracteres CJK).
2. Rama de trabajo: `feature/smart-match-explanation` (la actual).
3. Plantilla de fallback neutra y factual, sin «No se pudo generar»; coincidencia con
   las preferencias del estudiante, no con la universidad.
4. `price` y `budgetMax` como `Decimal` (ge 0, máximo 2 decimales), no `int`.
5. Servicios: rechazar solo caracteres de control y longitud > 40; sin regex
   restrictiva; delimitadores escapados en `to_context()`.

## Fuera de esta spec

Esta spec quedó `IMPLEMENTED` en la fase G04 sobre la rama `feature/smart-match-explanation`.
Se cierra como `IMPLEMENTED` solo con criterios verificados, gates en verde y evidencia
registrada. Siguen fuera de alcance el cálculo de Smart Match, la consulta de
propiedades, proveedores reales nuevos, autenticación de usuarios, mTLS, rotación de
secretos, rate limiting (005), moderación (006), observabilidad (007) y despliegue.
`004-natural-language-search` permanece `PLANNED` hasta que esta spec cierre.
