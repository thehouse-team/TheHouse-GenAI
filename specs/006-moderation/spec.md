# 006-moderation — Moderación de contenido

- **Estado:** ACTIVE
- **Depende de:** 002-provider-abstraction, 005-security, 011-llm-provider
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08
- **Fecha de activación:** 2026-11-18
- **Plan aprobado:** 2026-11-18
- **Última revisión:** 2026-11-18

## Objetivo

Definir una política y un puerto de moderación para la salida generativa, con
comportamiento seguro y trazable ante contenido dañino, sin depender del proveedor
generativo como único mecanismo de seguridad.

## Contexto

El servicio atiende a estudiantes y genera texto libre. Se necesita una política
explícita y un mecanismo desacoplado para bloquear contenido dañino sin filtrar el
contenido a logs. 003 ya valida la salida contra alucinaciones y rechaza los
`finishReason` de seguridad de Gemini; 005 endureció la autenticación, el rate limiting
y la defensa contra prompt injection. Esta spec **añade** una capa determinista local,
independiente del LLM, y refuerza la del proveedor con `safetySettings`.

El alcance aprobado es el **A**. La opción B (moderación de contenido de usuarios) queda
fuera y se documenta como deuda para una spec nueva si el requisito académico la exige.

## Alcance

### Incluido

- Política versionada (`moderation_v1`) de categorías, códigos de motivo y severidad.
- Puerto `ModerationProvider` independiente del proveedor, con fake y moderador local
  determinista (sin red, sin LLM y sin dependencias nuevas).
- Moderación de la **salida** de `explain-match` antes de responder, a través del puerto.
- Comportamiento fail-closed aprobado y versionado: fallback 200 con `generated=false`.
- `safetySettings` en `generateContent` como refuerzo del proveedor.
- Metadatos de auditoría sin contenido: decisión, categoría y versión de política.
- Pruebas con moderador fake y corpus benigno versionado.

### Excluido

- Moderación de contenido de usuarios (opción B: títulos, descripciones, reseñas,
  reportes) y su endpoint: queda para una spec nueva (deuda (f) en `memoria.md`).
- Uso del LLM como mecanismo de moderación; contratar un proveedor real de moderación.
- UI de moderación y revisión humana.
- Reemplazar la moderación existente del Backend.
- Asesoría legal definitiva.
- Cambios al contrato congelado de `explain-match`.

## Requisitos

- **RF-01:** política de categorías y severidad documentada y versionada como
  `moderation_v1`.
- **RF-02:** toda **salida** generativa pasa por el puerto de moderación. La entrada de
  `explain-match` sigue cubierta por 003/005: se delimita, se escapa y se registra como
  metadato seguro, sin rechazarse (005 D5).
- **RF-03:** contenido bloqueado no se envía al cliente; degrada a la plantilla de
  fallback con `generated=false`.
- **RF-04:** ante error o timeout del moderador se aplica la política fail-closed
  aprobada (A2): fallback 200, nunca un error para Backend ni un campo nuevo.
- **RF-05:** logs guardan decisión, categoría y versión de política, nunca el contenido.
- **RF-06:** los falsos positivos tienen ruta definida: la decisión adversa degrada a
  fallback y el motivo estable queda en logs para revisión; sin UI en esta spec.
- **RF-07:** los detectores son deterministas, locales, usan solo la stdlib y operan
  sobre texto normalizado, con coincidencia por palabra completa y allowlist de
  colisiones.
- **RF-08:** `safetySettings` viaja en la misma petición a Gemini: cero llamadas extra.

## Criterios de aceptación

- [ ] Política `moderation_v1` aprobada, versionada y probada.
- [ ] Puerto, fake y moderador local probados sin red.
- [ ] Correo, teléfono (10 dígitos, `+52` opcional) y URL (esquema o `www.`) en la salida
      degradan a fallback y no llegan al cliente.
- [ ] Léxico ofensivo es-MX por palabra completa, con allowlist de colisiones.
- [ ] El corpus benigno versionado de rentas estudiantiles no se bloquea.
- [ ] Salida adversa o error del moderador respeta el fail-closed (A2).
- [ ] Logs solo con metadatos permitidos; ningún texto moderado aparece en logs.
- [ ] `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE` presente en el payload, sin llamada
      extra y sin contenido en logs.
- [ ] La plantilla de fallback no incluye el título de la propiedad (A6).
- [ ] El contrato `{explanation, generated, promptVersion}` no cambia.
- [ ] `ruff check .`, `mypy src` y `pytest` en verde, sin red.

## Seguridad y privacidad

- No registrar texto moderado ni motivos con PII: solo códigos estables de categoría y
  motivo.
- Minimizar datos enviados al moderador: el moderador es local, así que el texto nunca
  sale del proceso.
- Limitar el tamaño del texto a moderar con el mismo tope de la explicación (900
  caracteres).
- Separar la decisión de moderación de la generación para poder auditarla.
- La plantilla de fallback no se modera porque se construye solo con datos estructurados
  y validados por Backend; desde A6 tampoco incluye el título libre del arrendador.

## Decisiones aprobadas

| # | Decisión |
| --- | --- |
| A1 | Alcance A únicamente: reglas deterministas locales sobre la salida más `safetySettings`. Sin endpoint de contenido de usuarios. |
| A2 | Fail-closed en salida: ante decisión adversa o error del moderador, 200 con `generated=false` y la plantilla de fallback; nunca 500 ni un campo nuevo. |
| A3 | `safetySettings`: cuatro categorías centrales con umbral `BLOCK_MEDIUM_AND_ABOVE`, constante en `providers/gemini.py`, sin variable de entorno nueva. Refuerzo del proveedor, no mecanismo de moderación. |
| A4 | Cero llamadas extra a Gemini. Sin modo híbrido en G06. |
| A5 | RF-02 reformulada: se modera la salida por el puerto; la entrada sigue cubierta por 003/005 (escape y registro, sin rechazo). |
| A6 | La plantilla de fallback no incluye el título de la propiedad: usa solo datos estructurados (score, precio con moneda, distancia, universidad y servicios). Contrato sin cambios. |
| A7 | Decisión anticipada para la opción B: fail-closed = `review`, LLM solo con flag opt-in. Sin implementar en G06. |

## Fuera de esta spec

El alcance A queda `ACTIVE` en G06 sobre la rama `feature/moderation`. La opción B
(moderación de contenido de usuarios) no se implementa: deuda (f) en `memoria.md` y
contrato propuesto en `plan.md`, para abrir como spec nueva si el requisito académico la
exige. Siguen fuera de alcance la UI de revisión humana, un proveedor real de
moderación, el uso del LLM como moderador y cualquier cambio al contrato de
`explain-match`.
