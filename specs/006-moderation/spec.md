# 006-moderation — Moderación de contenido

- **Estado:** PLANNED
- **Depende de:** 002-provider-abstraction, 005-security
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08

## Objetivo

Definir una política y un puerto de moderación para entradas y salidas generativas, con comportamiento seguro y trazable ante contenido dañino.

## Contexto

El servicio atiende a estudiantes y generará texto libre. Se necesita una política explícita y un mecanismo desacoplado para bloquear contenido dañino sin filtrar el contenido a logs.

## Alcance

### Incluido

- Política versionada de categorías prohibidas.
- Puerto de moderación independiente del proveedor.
- Moderación de entrada y salida antes de responder.
- Comportamiento fail-closed configurable.
- Metadatos de auditoría sin contenido sensible.
- Pruebas con moderador fake.

### Excluido

- Contratar un proveedor real de moderación.
- UI de moderación y revisión humana.
- Reemplazar la moderación existente del Backend.
- Asesoría legal definitiva.

## Requisitos

- **RF-01:** política de categorías y severidad documentada y versionada.
- **RF-02:** toda entrada y salida generativa pasa por el puerto de moderación.
- **RF-03:** contenido bloqueado no se envía al cliente.
- **RF-04:** ante error del moderador se aplica la política fail-closed aprobada.
- **RF-05:** logs guardan decisión y categoría, nunca el contenido.
- **RF-06:** falsos positivos tienen ruta de revisión definida.

## Criterios de aceptación

- [ ] Política aprobada y versionada.
- [ ] Puerto e implementación fake probados.
- [ ] Entrada/salida bloqueada no llega al usuario.
- [ ] Error del moderador respeta fail-closed.
- [ ] Logs sin contenido sensible.
- [ ] Pruebas de categorías y falsos positivos.

## Seguridad y privacidad

- No registrar texto moderado ni motivos detallados con PII.
- Minimizar datos enviados al moderador.
- Limitar tamaño de texto a moderar.
- Separar decisión de moderación de la generación para poder auditarla.

## Fuera de esta spec

No se implementa nada de este documento en G01. La spec permanece PLANNED hasta que
el Backend, la seguridad y los contratos estén aprobados y sea su turno.
