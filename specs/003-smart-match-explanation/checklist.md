# Checklist — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** IMPLEMENTED

## Criterios de aceptación

- [x] Contrato request/response documentado y validado (camelCase con aliases).
- [x] Explicación de fixture cita solo hechos permitidos.
- [x] Se rechazan números y servicios ausentes en la entrada.
- [x] Un porcentaje distinto de `matchScore` se rechaza y degrada a fallback.
- [x] `delpresupuesto` y `conuna` se rechazan con `MALFORMED_TEXT`, sin marcar
      palabras válidas como `porque` o `conde`.
- [x] La normalización corrige `cuesta$2,800` y `1.3 km,estando` sin alterar `1.3`,
      `2,800`, `$3,000 MXN` ni `91%`; «91 por ciento» se acepta.
- [x] Las respuestas reales de Gemini se usan como fixtures: la normal se acepta y la
      de `delpresupuesto` degrada a fallback.
- [x] `promptVersion` es `explain_match_v3` y el prompt incluye sus nuevas reglas.
- [x] El logger `httpx` queda en WARNING.
- [x] Prompt injection en título, universidad y servicios (incluido `</untrusted_data>`)
      no cambia reglas ni hechos.
- [x] Score faltante o fuera de rango devuelve 422.
- [x] `locale` distinto de `es-MX` y monedas dispares devuelven 422.
- [x] `price` y `budgetMax` rechazan más de 2 decimales.
- [x] Pruebas con fake provider, sin red.
- [x] No existe acceso a base de datos ni a propiedades.
- [x] Fallo/timeout del proveedor y salida rechazada devuelven 200 con
      `generated=false`, nunca 502.
- [x] `provider_model` y cualquier detalle del proveedor no aparecen en la respuesta.
- [x] Endpoint sin `X-Service-Key` devuelve 401 con el sobre estándar.
- [x] `X-Service-Key` incorrecto devuelve 401 sin revelar si la credencial existe.
- [x] La autenticación se evalúa antes de validar el body.
- [x] La credencial no aparece en logs ni en el `repr` de `Settings`.

## Seguridad

- [x] Minimizar PII: sin nombre de propietario, dirección exacta ni tokens.
- [x] No registrar prompt ni explicación completos por defecto.
- [x] Defensa contra prompt injection en todos los campos de texto libre.
- [x] Limitar longitud de entrada y salida.
- [x] Autenticación mínima de servicio implementada (`X-Service-Key`, `SecretStr`,
      comparación en tiempo constante, 401 con el sobre estándar).
- [x] La autenticación endurecida (rotación, mTLS, rate limiting) queda para la spec 005.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores.
- [x] `pytest` en verde y sin red.
- [x] Sin secretos, PII ni tokens en código, logs o fixtures.
- [x] Sin endpoints ni proveedores reales fuera de alcance.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.
- [x] Decisión D18 de timeouts documentada en spec/plan/.env.example/memoria sin
      cambiar el default de `Settings`.

## Corrección G10 (2026-11-26)

- [x] Los servicios recibidos se enmascaran antes de buscar servicios conocidos, de
      más largo a más corto, con `\b` y `re.escape`.
- [x] Se aceptan etiquetas compuestas recibidas («agua caliente», «baño privado») y se
      siguen rechazando servicios no recibidos («estacionamiento», «agua» suelto).
- [x] «gastos» no se confunde con el servicio «gas».
- [x] Gates en verde y evidencia registrada; spec sigue `IMPLEMENTED`.

## Corrección G10 sobre códigos universitarios (2026-11-27)

- [x] Los 10 códigos del catálogo, incluidos los seis con guion, se aceptan al ser
      mencionados junto a `MXN`.
- [x] `request.university` se enmascara con `(?<![\w-])` + `re.escape` + `(?![\w-])`
      antes de las validaciones de moneda y siglas (y del detector de palabras pegadas).
- [x] `_ACRONYM_PATTERN` detecta un código distinto con guion como un solo token.
- [x] Las partes del código no se añaden a las siglas permitidas: `UMB` solo →
      `FOREIGN_CURRENCY` y `ESTE` solo → `FOREIGN_UNIVERSITY`.
- [x] `USD` sigue siendo `FOREIGN_CURRENCY`; el orden de validaciones no cambia.
- [x] Gates en verde y evidencia registrada; spec sigue `IMPLEMENTED`.
