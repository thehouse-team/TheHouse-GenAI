# 005-security — Seguridad de servicio e IA

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction, 003, 004
- **Habilita:** 006, 007, 009, 010
- **Fecha de alta:** 2026-11-08

## Objetivo

Completar la postura de seguridad para un servicio interno de IA: autenticación servicio-a-servicio, minimización de PII, defensa contra prompt injection, límites y protección de secretos.

## Contexto

G01 ya aplica límites de request, CORS restrictivo, errores seguros y logs estructurados. Antes de exponer endpoints generativos se necesita autenticación de servicio, filtros de PII y controles formales de abuso.

## Alcance

### Incluido

- Threat model y data flow Backend → GenAI → proveedor.
- Autenticación servicio-a-servicio; nunca JWT de usuario final.
- Allowlist de campos por endpoint y filtro de PII previo al prompt.
- Redacción centralizada de secretos y datos sensibles en logs.
- Controles de prompt injection y validación de salida.
- Rate limiting y presupuestos de entrada/salida.
- Rotación de secretos, escaneo de dependencias y de secretos en CI.
- Pruebas de seguridad y runbook de incidentes.

### Excluido

- Autenticación de usuarios finales y gestión de sesiones.
- Pentest externo y cumplimiento legal completo.
- Infraestructura de despliegue y CD.

## Requisitos

- **RF-01:** solo health es público; todo endpoint generativo exige autenticación de servicio.
- **RF-02:** se rechazan y no se reenvían access/refresh tokens de usuario.
- **RF-03:** cada endpoint define allowlist de campos y rechaza PII innecesaria.
- **RF-04:** logs y errores redactan tokens, API keys, passwords y PII.
- **RF-05:** rate limit por servicio y presupuesto de tokens/tiempo.
- **RF-06:** CI detecta secretos y dependencias vulnerables.
- **RF-07:** intentos de prompt injection se registran como metadato seguro.

## Criterios de aceptación

- [ ] Threat model y data flow documentados.
- [ ] Endpoint generativo sin credencial devuelve 401 con sobre estándar.
- [ ] Tokens de usuario rechazados/no reenviados.
- [ ] Pruebas de PII y redacción de logs pasan.
- [ ] Corpus de prompt injection no altera contratos.
- [ ] Rate limit probado.
- [ ] Escaneo de secretos y dependencias en CI.

## Seguridad y privacidad

- Secretos solo en entorno/gestor; nunca en repo, imagen ni logs.
- Autenticación de servicio con secreto rotable o mTLS acordado con Backend.
- Defensa en profundidad: validación de entrada, prompt delimitado, validación de salida.
- Minimización estricta de PII; rechazar dirección exacta y datos del propietario.
- Fail closed: si falla la autenticación o validación, no se llama al proveedor.

## Fuera de esta spec

No se implementa nada de este documento en G01. La spec permanece PLANNED hasta que
el Backend, la seguridad y los contratos estén aprobados y sea su turno.
