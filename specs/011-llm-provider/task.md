# Tareas — 011-llm-provider Proveedor LLM real

- **Estado:** ACTIVE

> Spec activa desde 2026-11-15, con el plan aprobado y la decisión de proveedor
> documentada en `decision.md`. Ejecutar por bloques, dejando el repositorio verde
> en cada uno.

## Bloques

- [x] **B1** — Activación, evaluación y decisión: cabeceras de la spec, `memoria.md`,
      `evaluation.md`, `decision.md`, `README.md`.
- [ ] **B2** — Configuración validada: `Literal["fake", "gemini"]`, vacíos como
      `None`, credencial y modelo obligatorios con proveedor `gemini`.
- [ ] **B3** — Adaptador: mapeo de request y respuesta, cliente inyectable.
- [ ] **B4** — Adaptador: mapeo de errores, timeout y logging del modelo interno.
- [ ] **B5** — Factory: registro de `gemini` y `ProviderConfigurationError`.
- [ ] **B6** — Frontera de imports: `httpx` permitido solo en `providers/gemini.py`.
- [ ] **B7** — Smoke test manual opt-in, fuera de CI.
- [ ] **B8** — Ejecución del smoke test con credencial real y registro de la evidencia.
- [ ] **B9** — Cierre de la spec.

## Evaluación

- [x] Recopilar precio por millón de tokens de los tres candidatos (la cifra exacta
      de Gemini queda pendiente del id final de `GENAI_MODEL`).
- [x] Recopilar capa gratuita, límites y condiciones.
- [ ] Referenciar latencia típica y p95 por candidato. Pendiente del smoke test (B8).
- [x] Verificar salida JSON estructurada nativa.
- [ ] Evaluar calidad en español con casos representativos. Pendiente del smoke test
      (B8).
- [x] Verificar integración oficial en Python y mantenimiento del SDK.
- [x] Redactar matriz comparativa y documento de decisión.

## Implementación

- [ ] Implementar el adaptador del proveedor elegido sobre `providers/base.py`.
- [ ] Normalizar la respuesta al DTO interno.
- [ ] Mapear errores del vendor a la taxonomía propia.
- [ ] Registrar el proveedor en la factory y validar su configuración.
- [ ] Mantener la credencial como `SecretStr` y redactarla en logs.
- [ ] Registrar el identificador del modelo solo en logs y metadatos internos, nunca en
      las respuestas de la API.

## Pruebas y cierre

- [ ] Añadir tests de contrato del adaptador con dobles, sin red.
- [ ] Añadir tests de timeout, límites y mapeo de errores.
- [ ] Añadir test de frontera de imports (sin SDK del vendor).
- [ ] Añadir test que verifique que el modelo no aparece en el payload de respuesta.
- [ ] Escribir el script de smoke test manual opt-in.
- [ ] Ejecutar ruff, mypy y pytest.
- [ ] Actualizar checklist, evidence y memoria.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
