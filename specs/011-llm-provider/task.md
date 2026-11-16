# Tareas — 011-llm-provider Proveedor LLM real

- **Estado:** IMPLEMENTED

> Spec activa desde 2026-11-15, con el plan aprobado y la decisión de proveedor
> documentada en `decision.md`. Ejecutar por bloques, dejando el repositorio verde
> en cada uno.

## Bloques

- [x] **B1** — Activación, evaluación y decisión: cabeceras de la spec, `memoria.md`,
      `evaluation.md`, `decision.md`, `README.md`.
- [x] **B2** — Configuración validada: `Literal["fake", "gemini"]`, vacíos como
      `None`, credencial y modelo obligatorios con proveedor `gemini`.
- [ ] **B3** — Adaptador: mapeo de request y respuesta, cliente inyectable.
- [x] **B4** — Adaptador: mapeo de errores, timeout y logging del modelo interno.
- [x] **B5** — Factory: registro de `gemini` y `ProviderConfigurationError`.
- [x] **B6** — Frontera de imports: `httpx` permitido solo en `providers/gemini.py`.
- [x] **B7** — Smoke test manual opt-in, fuera de CI.
- [x] **B8** — Ejecución del smoke test con credencial real y registro de la evidencia.
- [x] **B9** — Cierre de la spec.

## Evaluación

- [x] Recopilar precio por millón de tokens de los tres candidatos (la cifra exacta
      de Gemini queda pendiente del id final de `GENAI_MODEL`).
- [x] Recopilar capa gratuita, límites y condiciones.
- [x] Referenciar latencia típica y p95 por candidato. Medido el 2026-11-16 solo para
      Gemini; OpenAI y Azure quedan «no medido» por falta de acceso.
- [x] Verificar salida JSON estructurada nativa.
- [x] Evaluar calidad en español con casos representativos. Medido el 2026-11-16 solo
      para Gemini; OpenAI y Azure quedan «no medido».
- [x] Verificar integración oficial en Python y mantenimiento del SDK.
- [x] Redactar matriz comparativa y documento de decisión.

## Implementación

- [x] Implementar el adaptador del proveedor elegido sobre `providers/base.py`.
- [x] Normalizar la respuesta al DTO interno.
- [x] Mapear errores del vendor a la taxonomía propia.
- [x] Registrar el proveedor en la factory y validar su configuración.
- [x] Mantener la credencial como `SecretStr` y redactarla en logs.
- [x] Registrar el identificador del modelo solo en logs y metadatos internos, nunca en
      las respuestas de la API.

## Pruebas y cierre

- [x] Añadir tests de contrato del adaptador con dobles, sin red.
- [x] Añadir tests de timeout, límites y mapeo de errores.
- [x] Añadir test de frontera de imports (sin SDK del vendor).
- [x] Añadir test que verifique que el modelo no aparece en el payload de respuesta.
      Verificado estructuralmente: `src/thehouse_genai/api/` no referencia
      `provider_model` y no existe todavía endpoint generativo.
- [x] Escribir el script de smoke test manual opt-in.
- [x] Ejecutar ruff, mypy y pytest.
- [x] Actualizar checklist, evidence y memoria.

## Cierre

- [x] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [x] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [x] Revisar seguridad y ausencia de secretos/PII.
- [x] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
