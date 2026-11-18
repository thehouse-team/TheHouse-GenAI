# Checklist — 007-observability Observabilidad

- **Estado:** IMPLEMENTED

## Criterios de aceptación

- [x] Schema de logs documentado (apéndice A) y probado.
- [x] Métricas expuestas internamente con nombres estables y etiquetas acotadas.
- [x] Una request completa se correlaciona por `request_id` en API, proveedor y caso de uso.
- [x] SLOs y alertas aprobados y documentados para G10 (apéndice B de `spec.md`).
- [x] Pruebas garantizan ausencia de contenido sensible en logs y en el snapshot JSON.
- [x] Coste y tokens medidos sin almacenar texto.
- [x] Presupuesto diario sin llamada a Gemini al agotarse; contrato intacto.
- [x] `/internal/metrics` y `/internal/health/detail` protegidos con clave separada.
- [x] `/health/live`, `/health/ready` y su payload sin cambios.
- [x] Sin dependencias nuevas; suite 100% sin red (775 tests).

## Seguridad

- [x] No incluir contenido de prompts/respuestas en logs, métricas ni correlación.
- [x] No incluir headers de autenticación ni la clave presentada.
- [x] Limitar cardinalidad de etiquetas a enums cerrados y rutas acotadas.
- [x] `GENAI_METRICS_KEY` como `SecretStr | None`, fail closed, nunca logueada.
- [x] `request_id` nunca enviado a Gemini; `provider_model` nunca expuesto en métricas.

## SDD y calidad

- [x] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [x] `ruff check .` sin hallazgos.
- [x] `mypy src` sin errores (32 archivos).
- [x] `pytest` en verde y sin red.
- [x] `git diff --check` limpio.
- [x] Sin secretos, PII ni tokens en código, logs o fixtures.
- [x] Sin endpoints ni proveedores reales fuera de alcance.
- [x] Evidencia registrada antes de marcar IMPLEMENTED.
