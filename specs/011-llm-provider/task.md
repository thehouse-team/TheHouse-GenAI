# Tareas — 011-llm-provider Proveedor LLM real

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Evaluación

- [ ] Recopilar precio por millón de tokens de los tres candidatos.
- [ ] Recopilar capa gratuita, límites y condiciones.
- [ ] Referenciar latencia típica y p95 por candidato.
- [ ] Verificar salida JSON estructurada nativa.
- [ ] Evaluar calidad en español con casos representativos.
- [ ] Verificar integración oficial en Python y mantenimiento del SDK.
- [ ] Redactar matriz comparativa y documento de decisión.

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
