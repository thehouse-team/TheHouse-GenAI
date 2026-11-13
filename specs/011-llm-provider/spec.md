# 011-llm-provider — Proveedor LLM real

- **Estado:** PLANNED
- **Depende de:** 002-provider-abstraction
- **Habilita:** 003, 004
- **Fecha de alta:** 2026-11-12

## Objetivo

Elegir y conectar un proveedor LLM real detrás del puerto `GenerativeAiProvider`,
manteniendo el resto del servicio agnóstico al vendor y sin red en las pruebas.

## Contexto

G02 entrega el puerto `GenerativeAiProvider` y un doble de test, pero ningún proveedor
real. Para exponer endpoints generativos hace falta un adaptador que hable con un
proveedor, con criterios objetivos de selección y sin acoplar la aplicación al SDK.

## Alcance

### Incluido

- Matriz de evaluación de proveedores (Gemini, OpenAI, Azure OpenAI) con criterios
  cuantificables: precio por millón de tokens, capa gratuita disponible, latencia típica,
  salida JSON estructurada nativa, calidad en español e integración oficial en Python.
- Documento de decisión con el proveedor elegido, la alternativa descartada y el motivo.
- Adaptador del proveedor elegido implementando `GenerativeAiProvider` detrás del puerto,
  sin cambios en application ni domain.
- Normalización de la respuesta del vendor y mapeo de sus errores a la taxonomía propia.
- Configuración por entorno de modelo, credencial, timeout y límite de entrada, con la
  credencial como `SecretStr`.
- Tests del adaptador sin red: contrato, parseo de respuesta, mapeo de errores y ausencia
  de llamadas reales.
- Script de smoke test manual, opt-in y fuera de CI, para validar una credencial real.

### Excluido

- Multi-proveedor simultáneo, failover y routing por coste.
- Prompts de negocio, endpoints generativos, moderación y streaming.
- Cambios en el contrato de `explain-match` o `parse-search`.
- CD, despliegue y secretos versionados.
- Llamadas de red dentro de CI o de la suite de pruebas.

## Requisitos

- **RF-01:** la evaluación compara los tres candidatos con los mismos criterios y una
  fuente citada por dato.
- **RF-02:** la decisión queda documentada con proveedor elegido, alternativa y
  condiciones de revisión.
- **RF-03:** el adaptador implementa `GenerativeAiProvider` sin cambios en application.
- **RF-04:** la respuesta del vendor se valida y se normaliza al DTO interno.
- **RF-05:** los errores del vendor se mapean a la taxonomía propia sin exponer su cuerpo
  ni su detalle al cliente.
- **RF-06:** la credencial es `SecretStr` y no aparece en logs, `repr` ni errores.
- **RF-07:** toda llamada tiene timeout y la entrada está acotada antes de salir.
- **RF-08:** la suite corre sin red; el smoke test manual es opt-in y CI nunca lo ejecuta.
- **RF-09:** el modelo y su versión se registran solo en logs y metadatos internos; nunca
  en las respuestas de la API, porque el Backend y Mobile no deben conocer el modelo
  interno.

## Criterios de aceptación

- [ ] Matriz de evaluación completa con los seis criterios y fuentes citadas.
- [ ] Documento de decisión aprobado con proveedor elegido y motivo.
- [ ] Adaptador implementando `GenerativeAiProvider` y registrado en la factory.
- [ ] Test de contrato del adaptador en verde con dobles, sin red.
- [ ] Errores 401/429/5xx del vendor mapeados a la taxonomía propia.
- [ ] La credencial no aparece en logs, `repr` ni respuestas.
- [ ] Timeout y límite de entrada verificados.
- [ ] El modelo y su versión aparecen en logs internos y en ninguna respuesta de la API.
- [ ] Script de smoke test manual documentado y fuera de CI.
- [ ] `ruff check .`, `mypy src` y `pytest` en verde sin acceso a red.

## Seguridad y privacidad

- La credencial vive solo en entorno o gestor de secretos; nunca en el repositorio.
- No registrar prompts ni respuestas completas; solo metadatos y longitudes.
- Redactar `Authorization` y claves del vendor en logs y excepciones.
- El smoke test manual exige confirmación explícita y no imprime la clave.
- El contexto enviado al provider contiene solo campos allowlist; sin PII.
- El identificador del modelo es información interna: solo va a logs, nunca a la API.

## Fuera de esta spec

Esta spec permanece `PLANNED` hasta que sea su turno. No se activa hasta que el plan esté
aprobado y exista una decisión de proveedor documentada.
