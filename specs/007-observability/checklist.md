# Checklist — 007-observability Observabilidad

- **Estado:** ACTIVE

## Criterios de aceptación

- [ ] Schema de logs documentado (apéndice A) y probado.
- [ ] Métricas expuestas internamente con nombres estables y etiquetas acotadas.
- [ ] Una request completa se correlaciona por `request_id` en API, proveedor y caso de uso.
- [ ] SLOs y alertas aprobados y documentados para G10.
- [ ] Pruebas garantizan ausencia de contenido sensible en logs y en el snapshot JSON.
- [ ] Coste y tokens medidos sin almacenar texto.
- [ ] Presupuesto diario sin llamada a Gemini al agotarse; contrato intacto.
- [ ] `/internal/metrics` y `/internal/health/detail` protegidos con clave separada.
- [ ] `/health/live`, `/health/ready` y su payload sin cambios.
- [ ] Sin dependencias nuevas; suite 100% sin red.

## Seguridad

- [ ] No incluir contenido de prompts/respuestas en logs, métricas ni correlación.
- [ ] No incluir headers de autenticación ni la clave presentada.
- [ ] Limitar cardinalidad de etiquetas a enums cerrados y rutas acotadas.
- [ ] `GENAI_METRICS_KEY` como `SecretStr | None`, fail closed, nunca logueada.
- [ ] `request_id` nunca enviado a Gemini; `provider_model` nunca expuesto en métricas.

## SDD y calidad

- [ ] `spec.md`, `plan.md`, `task.md`, `checklist.md` y `evidence.md` actualizados.
- [ ] `ruff check .` sin hallazgos.
- [ ] `mypy src` sin errores.
- [ ] `pytest` en verde y sin red.
- [ ] `git diff --check` limpio.
- [ ] Sin secretos, PII ni tokens en código, logs o fixtures.
- [ ] Sin endpoints ni proveedores reales fuera de alcance.
- [ ] Evidencia registrada antes de marcar IMPLEMENTED.
