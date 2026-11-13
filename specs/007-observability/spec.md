# 007-observability — Observabilidad

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction, 005-security
- **Habilita:** 009-ci-cd, 010-integration-thehouse
- **Fecha de alta:** 2026-11-08

## Objetivo

Dar visibilidad operativa al servicio sin exponer prompts, respuestas ni PII: métricas, trazas, logs correlacionados, SLOs y alertas.

## Contexto

G01 ya emite logs JSON con request ID y health probes. Al añadir LLM se necesita medir latencia, errores, uso y coste, y correlacionar Backend → GenAI → proveedor.

## Alcance

### Incluido

- Schema de logs estable y allowlist de campos.
- Métricas de request, latencia, errores, rate limit y proveedor.
- Trazas con request ID y propagación de contexto.
- SLOs, dashboards y alertas propuestos.
- Métricas de tokens y coste sin contenido.
- Política de retención y muestreo.

### Excluido

- Contratar APM y desplegar dashboards en producción.
- Registrar prompts/respuestas completos.
- Traza de datos de usuario o PII.

## Requisitos

- **RF-01:** todo log usa JSON con timestamp, nivel, mensaje y request ID.
- **RF-02:** métricas cubren latencia, errores por código, proveedor y saturación.
- **RF-03:** nunca se registran prompts, respuestas, tokens de usuario ni PII.
- **RF-04:** request ID se propaga al proveedor cuando sea seguro.
- **RF-05:** SLOs y alertas documentados con umbrales.
- **RF-06:** muestreo y retención definidos.

## Criterios de aceptación

- [ ] Schema de logs documentado y probado.
- [ ] Métricas expuestas internamente con nombres estables.
- [ ] Trazas correlacionan una request completa.
- [ ] SLOs y alertas aprobados.
- [ ] Pruebas garantizan ausencia de contenido sensible.
- [ ] Coste/tokens medidos sin almacenar texto.

## Seguridad y privacidad

- No incluir contenido de prompts/respuestas en logs, métricas ni trazas.
- No incluir headers de autenticación.
- Limitar cardinalidad de etiquetas para evitar PII.
- Proteger endpoint de métricas en red interna.

## Fuera de esta spec

Esta spec permanece `PLANNED` hasta que sea su turno. No se activa hasta que su plan
esté aprobado.
