# 004-natural-language-search — Búsqueda en lenguaje natural

- **Estado:** ACTIVE
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  005-security, 006-moderation, 007-observability, 011-llm-provider
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08
- **Activada:** 2026-11-18, con plan aprobado y decisiones D1–D13 registradas en `memoria.md`
- **Última revisión:** 2026-11-18

## Objetivo

Convertir una consulta en lenguaje natural en filtros estructurados y validados. GenAI
nunca devuelve propiedades, no consulta catálogos ni ejecuta búsquedas: el Backend sigue
siendo el único que decide qué propiedades existen y valida los filtros contra sus
propios catálogos antes de buscar.

## Contexto

G04 entregó `explain-match`, su contrato camelCase, el fallback seguro y la autenticación
mínima; G05 añadió rotación de clave, rate limit, allowlist de campos del prompt, corpus
de inyección y redacción de metadatos; G06 añadió la política `moderation_v1`, el puerto
de moderación y la moderación de salida; G07 añadió métricas de enum cerrado, presupuesto
diario, endpoints internos y correlación por `request_id`; G03 conectó el adaptador real
de Gemini detrás del puerto de 002. Esta spec **reutiliza** todas esas capacidades y no
las rehace.

A diferencia de `explain-match`, aquí el texto libre del estudiante entra al prompt. Por
ello la query es UNTRUSTED: se delimita, se escapa, se analiza contra inyección y se le
redactan correos, teléfonos y URLs **antes** de enviarla al proveedor.

## Alcance

### Incluido

- Contrato HTTP `POST /api/v1/generative/parse-search`, camelCase en el alambre con
  aliases sobre modelos Python snake_case y `extra="forbid"` en todos los objetos.
- Filtros acotados: `maxBudget`, `currency`, `university`, `essentialServices`,
  `petsAllowed` y `maxDistanceKm`.
- Prompt versionado `parse_search_v1` con salida JSON estructurada: el modelo devuelve
  **solo** `{"filters": {...}}`; `confidence`, `generated` y `promptVersion` los produce
  el servicio.
- Validación anti-alucinación por evidencia: cada filtro debe estar respaldado por el
  texto normalizado del usuario; lo no respaldado se poda, no se rechaza la respuesta.
- Normalización es-MX de dinero (`$3,000`, `3 mil`, `3k`, `3.5 mil`, `menos de 3000`) y
  de distancia (`1.3 km`, `2 kilómetros`, `a menos de 2 km`).
- `confidence` determinista (`high`/`medium`/`low`), nunca tomada del modelo.
- Redacción de PII antes del prompt reutilizando los detectores de `domain/moderation.py`.
- Moderación determinista de la **entrada** (fail closed sin llamada al proveedor) y de
  la **salida** a través del puerto de 006.
- Reutilización de `X-Service-Key` con rotación, rate limit, presupuesto diario, métricas
  con etiquetas cerradas, `safetySettings` y fallback 200.
- Corpus versionado de 28 frases es-MX con filtros esperados y script manual opt-in de
  prueba con Gemini real, sin red en la suite automática.

### Excluido

- Devolver propiedades, IDs, direcciones, precios de listados ni resultados de búsqueda.
- Consultar propiedades, catálogos del Backend ni calcular Smart Match.
- Convertir monedas, minutos o cuadras a distancia, ni otras monedas a MXN.
- Catálogos de universidades o servicios enviados en el request o configurados en GenAI:
  GenAI solo extrae lo que el usuario escribió; Backend mapea y valida (decisión D2).
- Ordenar, paginar, autenticar usuarios finales, mTLS, desplegar ni añadir dependencias.
- Moderación con LLM, proveedor de moderación externo ni UI de revisión humana.

## Requisitos

- **RF-01:** la respuesta es exactamente `{filters, confidence, generated, promptVersion}`
  (D1). `promptVersion` es constante del servicio (`parse_search_v1`), nunca se deriva
  del proveedor.
- **RF-02:** `filters` contiene exactamente `maxBudget`, `currency`, `university`,
  `essentialServices`, `petsAllowed` y `maxDistanceKm` (ajuste 1). `extra="forbid"`
  rechaza cualquier campo de propiedad o resultado de búsqueda.
- **RF-03:** `maxBudget` es `Decimal | null` internamente (≥ 0, ≤ 2 decimales y
  ≤ 1,000,000) y número JSON en el alambre, nunca string. Solo se emite si hay dinero
  explícito en la query: `$3,000`, `3 mil`, `3k`, `3.5 mil`,
  `menos de 3000`, `hasta 3 mil`, `presupuesto de 3000`. `2026`, `1.3 km` y un teléfono
  de 10 dígitos no son dinero.
- **RF-04:** `currency` es `null` o `"MXN"` (D4). Es `null` sin dinero y `"MXN"` cuando
  hay dinero sin moneda explícita. Si la query menciona otra moneda de forma explícita,
  se descarta `maxBudget`, se deja `currency=null` y baja la confianza. Nunca se inventa
  una conversión.
- **RF-05:** `university` se emite solo si el valor normalizado (sin acentos, minúsculas,
  palabra completa) aparece en la query **o** si es la forma canónica de un alias
  presente en la tabla de alias en código (por ahora `UTTT` y su nombre completo). Sin
  evidencia, se poda (ajuste 2).
- **RF-06:** `essentialServices` contiene solo servicios mencionados, del vocabulario
  cerrado `internet`, `agua`, `luz`, `gas`, `estacionamiento`, `lavadora`, `amueblado`,
  `baño privado`, con sinónimos deterministas (`wifi`→`internet`, etc.). `mascotas` no
  aparece aquí: pertenece a `petsAllowed`.
- **RF-07:** `petsAllowed` solo se emite como `true` ante mención positiva de mascotas;
  las menciones negativas ("sin mascotas", "no acepto mascotas") dejan el filtro en
  `null` (D5).
- **RF-08:** `maxDistanceKm` es `Decimal | null` internamente (≥ 0 y ≤ 100) y número
  JSON en el alambre (con decimales cuando los tiene), nunca string. Solo se emite ante
  un número seguido de `km`, `kms`, `kilómetro(s)`. Minutos y cuadras no se convierten
  (ajuste 1). `3 km` es distancia; `3k` es dinero.
- **RF-09:** "entre 2000 y 3000" produce `maxBudget=3000` (tope del rango) y la
  confianza no supera `medium` (ajuste 3).
- **RF-10:** la query mide entre 1 y 500 caracteres, sin caracteres de control. Vacía,
  solo espacios u oversized → 422 con el sobre estándar (D3). Una query válida pero
  incomprensible, o que queda vacía tras redactar PII, → 200 con filtros vacíos y
  `confidence=low`.
- **RF-11:** el completion del modelo contiene solo `{"filters": {...}}`. Cualquier
  campo extra (incluido `confidence` o `generated`) se rechaza como `INVALID_JSON` y
  degrada a fallback. La confianza es determinista (D7).
- **RF-12:** `confidence=high` si `grounded ≥ 2`, sin filtros podados y sin rango de
  dinero; `medium` si `grounded == 1`, o hay filtros podados, o el dinero viene de un
  rango; `low` si no hay proveedor, falla el proveedor, el JSON es inválido, la
  moderación bloquea, el presupuesto se agota, `grounded == 0` o hay otra moneda.
  `grounded` cuenta los campos con filtro válido entre `maxBudget`, `university`,
  `petsAllowed` y `maxDistanceKm`, más cada servicio esencial (D7).
- **RF-13:** si tras la poda no queda ningún filtro, se responde 200 con
  `generated=false` y `confidence=low` (D6). `generated=true` solo si el modelo entregó
  un JSON válido y al menos un filtro sobrevivió a la validación.
- **RF-14:** ante fallo del proveedor, timeout, JSON inválido, moderación adversa,
  error del moderador o presupuesto agotado se responde **200** con filtros vacíos,
  `generated=false` y `confidence=low`. **No existe el 502** (003 D4, 006 A2, 007).
- **RF-15:** correos, teléfonos de 10 dígitos y URLs se redactan con `[EMAIL]`,
  `[TELEFONO]` y `[URL]` antes de construir el prompt, reutilizando las regex de
  `domain/moderation.py`. Si no queda texto tras redactar, no se llama al proveedor.
- **RF-16:** la query se delimita entre `<untrusted_data>` y se escapa con el guard de
  texto compartido. Los marcadores de inyección (incluidos homoglifos y caracteres de
  ancho cero) se detectan, se registran como metadato seguro y **no** rechazan la
  request (005 D5).
- **RF-17:** `classify()` de `moderation_v1` se aplica a la query antes del prompt. Ante
  decisión `block` o `review` se responde 200 vacío + `low` sin llamar al proveedor, con
  razón acotada `INPUT_MODERATION_BLOCKED` o `INPUT_MODERATION_REVIEW` (D8). La salida
  se modera por el puerto de 006 con fail-closed.
- **RF-18:** el endpoint exige `X-Service-Key` (rotación de 005) y aplica el rate limit
  antes del proveedor. Reutiliza el mismo `DailyBudget` y el mismo
  `GenerativeAiProvider` que `explain-match`.
- **RF-19:** las métricas añaden la ruta cerrada `parse-search`, outcomes por
  `generated`, confianza por enum cerrado y nuevas razones de fallback. Los logs
  correlacionan `request_id` también para `application.parse_search` (D10).
- **RF-20:** no se escriben caracteres CJK ni de ancho completo en ningún archivo
  (ajuste 4).

## Criterios de aceptación

- [ ] Contrato request/response validado con camelCase, `extra="forbid"` y `promptVersion`.
- [ ] `maxDistanceKm` distingue `3 km` de `3k`; minutos y cuadras no se convierten.
- [ ] El valor de `university` aparece en la query normalizada o es alias canónico.
- [ ] "entre 2000 y 3000" → `maxBudget=3000` y confianza como máximo `medium`.
- [ ] Cada filtro no respaldado se poda sin rechazar la respuesta.
- [ ] `confidence` no aparece en el completion: es determinista y calculada por el servicio.
- [ ] PII redactada antes del prompt; inyección escapada y registrada, nunca rechazada.
- [ ] Query ofensiva: 200 vacío + `low` y cero llamadas al proveedor.
- [ ] Salida moderada; decisión adversa o error degrade a 200 vacío + `low`.
- [ ] Fallo/timeout del proveedor y presupuesto agotado → 200, nunca 502.
- [ ] 401 sin credencial; 422 en query vacía/oversized; 429 con `Retry-After`.
- [ ] Corpus versionado de 28 frases + 2 casos de contrato, 100% sin red.
- [ ] Sin `provider_model`, propiedades ni PII en respuesta, logs, métricas ni fixtures.
- [ ] `ruff check .`, `mypy src` y `pytest` en verde.

## Seguridad y privacidad

- El query es dato no confiable: se normaliza, se modera, se redacta, se delimita y se
  escapa. Nunca se registran su contenido completo ni los cuerpos de request.
- Los secretos siguen en `Settings` como `SecretStr`; la clave de métricas es distinta de
  la de servicio; `request_id` nunca llega al proveedor.
- La allowlist de campos del prompt de 003 no cambia; el prompt de 004 solo incluye
  `query` (redactada) y `locale`.
- `safetySettings` de Gemini viajan en la misma petición, sin llamadas extra.

## Contrato HTTP

`POST /api/v1/generative/parse-search`. Nombres camelCase en el alambre, modelos Python
en snake_case con `Field(alias=...)` y `extra="forbid"` (D1).

Entrada:

```json
{"query": "Busco algo de máximo 3000 cerca de la UTTT con internet", "locale": "es-MX"}
```

- **Obligatorio:** `query` (1–500 caracteres, sin caracteres de control).
- **Opcional:** `locale` (default `es-MX`; cualquier otro valor → 422).

Salida:

```json
{
  "filters": {
    "maxBudget": 3000,
    "currency": "MXN",
    "university": "UTTT",
    "essentialServices": ["internet"],
    "petsAllowed": null,
    "maxDistanceKm": null
  },
  "confidence": "high",
  "generated": true,
  "promptVersion": "parse_search_v1"
}
```

`maxBudget` y `maxDistanceKm` viajan como números JSON (`int` o `float`, según tengan
decimales) o `null`; nunca como strings. Internamente el servicio conserva `Decimal`
para no perder exactitud. Backend los lee como decimal con `System.Text.Json`.

## Fallback

Ante cualquiera de las causas de RF-14 se responde 200 con:

```json
{
  "filters": {
    "maxBudget": null,
    "currency": null,
    "university": null,
    "essentialServices": [],
    "petsAllowed": null,
    "maxDistanceKm": null
  },
  "confidence": "low",
  "generated": false,
  "promptVersion": "parse_search_v1"
}
```

No se usa un extractor determinista para poblar el fallback (D9): el extractor de dinero
existe solo para validar la evidencia del modelo. El fallback no es un error para Backend.

## Decisiones aprobadas (D1–D13)

| # | Decisión |
| --- | --- |
| D1 | Añadir `promptVersion` a la respuesta; constante `parse_search_v1`. |
| D2 | Opción C: GenAI emite solo lo respaldado por el texto; sin catálogos en el request ni en `Settings`. Backend mapea y valida. |
| D3 | `query` de 1–500 caracteres; blank/oversized → 422; vago o solo-PII → 200 vacío + `low`. |
| D4 | Solo `MXN`: `null` sin dinero, `MXN` con dinero, otra moneda explícita → descartar `maxBudget`, `currency=null` y bajar confianza. |
| D5 | `petsAllowed` solo `true`; menciones negativas → `null`. |
| D6 | `generated=false` si se podan todos los filtros. |
| D7 | Fórmula de confianza de RF-12, contando también `maxDistanceKm` en `grounded`. |
| D8 | Moderación de entrada fail-closed sin llamada al proveedor; extensión documentada del alcance A de 006. |
| D9 | Fallback sin proveedor: filtros vacíos + `low`, sin extractor determinista. |
| D10 | Métricas y logs: ruta cerrada `parse-search`, nuevos contadores y razones, y filtro de `request_id` para `application.parse_search`. |
| D11 | Extraer el guard de texto a `domain/text_guard.py`, con re-exports para que los tests de 003 sigan verdes sin cambios. |
| D12 | Script manual nuevo `scripts/smoke_parse_search.py`, opt-in y nunca en CI. |
| D13 | Rama `feature/natural-language-search`. |

## Ajustes obligatorios incorporados

1. Filtro `maxDistanceKm` (`Decimal | null`, ≥ 0, ≤ 100) con evidencia de `km`, `kms` o
   `kilómetro(s)`. Minutos y cuadras no se convierten. Corpus: "a menos de 2 km de la
   UTTT", "a 10 minutos de la uni" → `null`, "3 km" vs "3k".
2. `university`: el valor devuelto debe aparecer en la query normalizada (sin acentos,
   minúsculas, palabra completa) o ser la forma canónica de un alias presente. Tabla de
   alias en código, por ahora UTTT y su nombre completo. Sin evidencia, se poda.
3. "entre 2000 y 3000" → `maxBudget=3000` (tope) con confianza máxima `medium`.
4. Sin caracteres CJK ni de ancho completo en ningún archivo.

## Fuera de esta spec

Queda fuera catálogos de Backend, conversión de monedas, minutos o cuadras, propiedades,
búsqueda, ordenación, paginación, Smart Match, autenticación de usuarios, mTLS,
despliegue y dependencias nuevas. `010-integration-thehouse` y `008-testing` cierran los
contract tests y la integración en G09/G10.
