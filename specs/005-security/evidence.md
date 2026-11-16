# Evidencia — 005-security Seguridad de servicio e IA

- **Estado:** IMPLEMENTED (alcance autorizado G05 para smart-match explanation; hardening global pendiente en spec 005 completa)
- **Fecha:** 2026-11-15
- **Rama:** `feature/smart-match-explanation`

## Comandos y resultados

| Comando | Resultado |
| --- | --- |
| `python -m ruff check .` | PASS |
| `python -m mypy src` | PASS |
| `python -m pytest` | `177 passed, 1 warning` |

## Controles implementados (alcance entregado)

- Autenticación servicio-a-servicio mínima para endpoint generativo: `X-Service-Key` en `Settings` como `SecretStr`, comparación `hmac.compare_digest`, `401` con sobre estándar; health público.
- Fail closed: sin credencial válida o sin provider/clave de provider configurada no se expone generación exitosa; errores mapeados de forma segura.
- PII/minimización: schemas `extra="forbid"` (allowlist efectiva), no se aceptan campos de usuario sensibles (nombre/email/teléfono/tokens/chats/reportes/códigos/etc.) en contrato; payload enviado al provider construido solo con datos mínimos permitidos y sanitizados.
- Prompt injection: campos tratados como datos, `system_prompt` defensivo, validación estricta de salida JSON/fidelidad y rechazo de instrucciones embebidas que intenten cambiar score/inventar/revelar secretos.
- Secretos: `GEMINI_API_KEY`/`GENAI_API_KEY`/`SERVICE_API_KEY` como `SecretStr`, placeholders en `.env.example`, no hardcodeados, no loggeados, no expuestos en respuestas/errores.
- Observabilidad segura: logs estructurados de metadatos (evento, éxito/fallo, latencia/tipo seguro) sin prompts completos con PII, sin API keys/JWT/payload sensible.

## Pendiente (fuera de este alcance autorizado / spec 005 global)

- Threat model y data flow documentados formalmente, runbook dedicado.
- Rate limiting por servicio y presupuestos globales.
- Escaneo de secretos/dependencias integrado en CI.
- Endurecimiento adicional de auth (rotación/mTLS negociado con Backend).
