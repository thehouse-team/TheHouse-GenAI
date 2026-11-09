# 003-smart-match-explanation — Explicación de Smart Match

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08

## Objetivo

Explicar en lenguaje natural un match score calculado externamente, usando solo los hechos y preferencias entregados por TheHouse Backend, sin alterar ningún dato.

## Contexto

Smart Match es una función ML del Backend. GenAI no lo calcula. El endpoint futuro recibe el score ya calculado y datos reales de propiedad/preferencias para redactar una explicación breve y fiel. En G01 no se implementa.

## Alcance

### Incluido

- Contrato futuro `POST /api/v1/generative/explain-match`.
- Validación de score, propiedad, universidad y preferencias mínimas.
- Prompt acotado y allowlist de hechos que pueden mencionarse.
- Validación de salida: sin números ni servicios no presentes en la entrada.
- Respuesta breve con `explanation` y `facts_used`.
- Pruebas con fake provider e intentos de prompt injection.

### Excluido

- Cálculo o recálculo de Smart Match.
- Consulta de propiedades, precios, distancias o disponibilidad.
- Dirección exacta, datos del propietario o PII innecesaria.
- Proveedor real y despliegue.

## Requisitos

- **RF-01:** `match_score` es obligatorio, entero 0–100 y se recibe ya calculado.
- **RF-02:** la explicación solo puede citar hechos de la allowlist de entrada.
- **RF-03:** no se inventan precios, distancias, servicios, universidad ni disponibilidad.
- **RF-04:** la salida no incluye un score propio ni modificado.
- **RF-05:** la explicación tiene un máximo de 120 palabras.
- **RF-06:** entradas inconsistentes o incompletas se rechazan con 422.
- **RF-07:** texto libre de propiedad se trata como dato, no como instrucción.

## Criterios de aceptación

- [ ] Contrato request/response documentado y validado.
- [ ] Explicación de fixture cita solo hechos permitidos.
- [ ] Se rechazan números y servicios ausentes en la entrada.
- [ ] Prompt injection en título/descripción no cambia reglas ni hechos.
- [ ] Score faltante o fuera de rango devuelve 422.
- [ ] Pruebas con fake provider, sin red.
- [ ] No existe acceso a base de datos ni a propiedades.

## Seguridad y privacidad

- Minimizar PII: sin nombre de propietario, dirección exacta ni tokens.
- No registrar prompt ni explicación completos por defecto.
- Defensa contra prompt injection en todos los campos de texto libre.
- Limitar longitud de entrada y salida.
- Autenticación servicio-a-servicio antes de exponer el endpoint (spec 005).

## Contrato futuro (referencia)

Entrada:

```json
{
  "match_score": 87,
  "property": {
    "id": "prop_123",
    "title": "Cuarto cerca de UTTT",
    "price": 2800,
    "currency": "MXN",
    "distance_km": 1.2,
    "services": ["internet", "agua"]
  },
  "university": {"name": "UTTT"},
  "preferences": {"budget_max": 3000, "required_services": ["internet"]}
}
```

Salida:

```json
{
  "explanation": "Coincide por precio dentro de tu presupuesto, cercanía y servicios requeridos.",
  "facts_used": ["match_score", "price", "distance_km", "services"]
}
```

El score no se devuelve ni se modifica; solo se usa como contexto.

## Fuera de esta spec

No se implementa nada de este documento en G01. La spec permanece PLANNED hasta que
el Backend, la seguridad y los contratos estén aprobados y sea su turno.
